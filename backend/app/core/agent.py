import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "get_available_datasets",
        "description": "List all available NASA Earth observation datasets in BHIMA with metadata.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_dataset_metadata",
        "description": "Get detailed metadata for a specific dataset including units, resolution, coverage period, and limitations.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {
                    "type": "string",
                    "description": "Dataset identifier, e.g. GPM_3IMERGM_07"
                }
            },
            "required": ["dataset_id"]
        }
    },
    {
        "name": "extract_regional_timeseries",
        "description": "Extract a time series of observations for a geographical region from a NASA dataset.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {
                    "type": "string",
                    "description": "Dataset ID, e.g. GPM_3IMERGM_07"
                },
                "region_name": {
                    "type": "string",
                    "description": "Human-readable name of the region"
                },
                "min_lon": {"type": "number", "description": "Minimum longitude in decimal degrees"},
                "max_lon": {"type": "number", "description": "Maximum longitude in decimal degrees"},
                "min_lat": {"type": "number", "description": "Minimum latitude in decimal degrees"},
                "max_lat": {"type": "number", "description": "Maximum latitude in decimal degrees"},
                "start_date": {"type": "string", "description": "Start date in YYYY-MM format"},
                "end_date": {"type": "string", "description": "End date in YYYY-MM format"}
            },
            "required": ["dataset_id", "region_name", "min_lon", "max_lon", "min_lat", "max_lat", "start_date", "end_date"]
        }
    },
    {
        "name": "calculate_trend",
        "description": "Calculate trend statistics for a previously extracted time series analysis. Returns Sen's slope, p-value, and trend direction.",
        "parameters": {
            "type": "object",
            "properties": {
                "analysis_id": {
                    "type": "string",
                    "description": "The analysis ID returned by extract_regional_timeseries"
                }
            },
            "required": ["analysis_id"]
        }
    },
    {
        "name": "compare_regions",
        "description": "Compare time series and trends between two geographical regions.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string"},
                "region_a_name": {"type": "string"},
                "region_a_min_lon": {"type": "number"},
                "region_a_max_lon": {"type": "number"},
                "region_a_min_lat": {"type": "number"},
                "region_a_max_lat": {"type": "number"},
                "region_b_name": {"type": "string"},
                "region_b_min_lon": {"type": "number"},
                "region_b_max_lon": {"type": "number"},
                "region_b_min_lat": {"type": "number"},
                "region_b_max_lat": {"type": "number"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            },
            "required": ["dataset_id", "region_a_name", "region_a_min_lon", "region_a_max_lon", "region_a_min_lat", "region_a_max_lat", "region_b_name", "region_b_min_lon", "region_b_max_lon", "region_b_min_lat", "region_b_max_lat", "start_date", "end_date"]
        }
    },
    {
        "name": "get_analysis_sources",
        "description": "Get the data sources, methodology, and citation information for a completed analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "analysis_id": {"type": "string"}
            },
            "required": ["analysis_id"]
        }
    }
]


class BHIMAAgent:
    """
    BHIMA AI Research Assistant.
    Uses official Google Gen AI Python SDK (Gemini Developer API) with function calling
    to invoke real backend analysis tools.
    """

    def __init__(
        self,
        api_key: Optional[str],
        data_accessor,
        analysis_engine,
        model_name: str = "gemini-2.5-flash"
    ):
        # Prioritize explicit api_key or GEMINI_API_KEY from server environment.
        # Explicitly avoid GOOGLE_API_KEY conflicting or overriding GEMINI_API_KEY.
        raw_key = api_key or os.environ.get("GEMINI_API_KEY") or ""
        self.api_key = raw_key.strip()
        self.has_api_key = bool(self.api_key and self.api_key != "your_gemini_key_here")
        self.data_accessor = data_accessor
        self.analysis_engine = analysis_engine
        self.model_name = model_name
        self._analysis_cache: Dict[str, Any] = {}
        self._current_tool_calls: List[Dict[str, Any]] = []

        self.client: Optional[genai.Client] = None
        if self.has_api_key:
            try:
                # Official Google Gen AI SDK initialized for Gemini Developer API.
                # Must use api_key directly with api_version='v1beta' for function calling support.
                # No Google Cloud ADC, no service account, no OAuth bearer tokens.
                self.client = genai.Client(
                    api_key=self.api_key,
                    http_options={"api_version": "v1beta"}
                )
                logger.info("Gemini Developer API client initialized successfully using google-genai SDK.")
            except Exception as e:
                safe_err = self._sanitize_error(str(e))
                logger.error(f"Failed to initialize Gemini Developer API client: {safe_err}")
                self.has_api_key = False
                self.client = None
        else:
            logger.warning("Gemini API key not configured. Agent will use fallback mode.")
            self.client = None

    def _sanitize_error(self, err_msg: str) -> str:
        """Strip any API key or sensitive token from error message to prevent leaks."""
        if not err_msg:
            return ""
        if self.api_key and self.api_key in err_msg:
            err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
        # Strip common AIza API key format if present
        err_msg = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_API_KEY]", err_msg)
        return err_msg

    def _system_prompt(self) -> str:
        return """You are BHIMA, an Earth System Intelligence research assistant built for NASA Space Apps Challenge.

Your role:
- Help users investigate Earth science data and environmental trends
- Use available tools to retrieve real NASA observations and compute actual statistics
- Explain scientific findings accurately and accessibly
- Always ground explanations in actual returned data, never invent statistics
- Distinguish measured observations from interpretations
- State limitations clearly
- Ask for clarification when region boundaries or time periods are ambiguous

Scientific rules:
- Never fabricate statistics or data values
- Never confuse correlation with causation
- Always cite the dataset and methodology used
- Explain uncertainty and data limitations
- If a tool fails, explain honestly what could not be computed

Workflow for investigation questions:
1. Identify the variable (precipitation, temperature, etc.)
2. Identify the region (get bounding box or ask user)
3. Identify the time period
4. Call extract_regional_timeseries to get real data
5. The trend is computed automatically in the analysis
6. Explain what the numbers mean, citing actual returned values
7. Reference limitations

Common bounding boxes for reference:
- Gujarat, India: min_lon=68.1, max_lon=74.5, min_lat=20.1, max_lat=24.7
- Central Gujarat (Vadodara): min_lon=73.1, max_lon=73.3, min_lat=22.1, max_lat=22.5
- Rajasthan, India: min_lon=69.5, max_lon=78.0, min_lat=23.0, max_lat=30.0
- Amazon Basin: min_lon=-73.0, max_lon=-50.0, min_lat=-15.0, max_lat=5.0
- Sahel Africa: min_lon=-15.0, max_lon=40.0, min_lat=10.0, max_lat=20.0
- California: min_lon=-124.5, max_lon=-114.1, min_lat=32.5, max_lat=42.0
- Murray-Darling Basin: min_lon=138.0, max_lon=149.0, min_lat=-37.0, max_lat=-24.0
- Monsoon Asia: min_lon=60.0, max_lon=110.0, min_lat=10.0, max_lat=35.0
- Sahara Desert: min_lon=-5.0, max_lon=35.0, min_lat=20.0, max_lat=30.0
- Great Plains, USA: min_lon=-104.0, max_lon=-96.0, min_lat=32.0, max_lat=48.0"""

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return structured result."""
        try:
            result: Dict[str, Any] = {}
            if tool_name == "get_available_datasets":
                result = {"datasets": self.data_accessor.get_all_datasets()}

            elif tool_name == "get_dataset_metadata":
                dataset_id = tool_args["dataset_id"]
                result = self.data_accessor.get_dataset_info(dataset_id)

            elif tool_name == "extract_regional_timeseries":
                df, notes, provenance, src, *extra = self.data_accessor.get_timeseries_data(
                    dataset_id=tool_args["dataset_id"],
                    min_lon=tool_args["min_lon"],
                    max_lon=tool_args["max_lon"],
                    min_lat=tool_args["min_lat"],
                    max_lat=tool_args["max_lat"],
                    start_date=tool_args["start_date"],
                    end_date=tool_args["end_date"],
                    region_name=tool_args.get("region_name"),
                )
                info = self.data_accessor.get_dataset_info(tool_args["dataset_id"])
                full_res = self.analysis_engine.run_full_analysis(
                    df=df,
                    dataset_id=tool_args["dataset_id"],
                    variable=info["variable"],
                    units=info["units"],
                    region_name=tool_args["region_name"],
                    source_description=info["description"],
                    processing_notes=notes,
                    data_provenance=provenance,
                    data_source=src
                )
                self._analysis_cache[full_res["analysis_id"]] = full_res
                # Provide concise summary to model to optimize prompt context
                result = {
                    "analysis_id": full_res["analysis_id"],
                    "region": full_res["timeseries"]["region"],
                    "dataset_id": full_res["timeseries"]["dataset_id"],
                    "variable": full_res["timeseries"]["variable"],
                    "units": full_res["timeseries"]["units"],
                    "period_start": full_res["timeseries"]["start_date"],
                    "period_end": full_res["timeseries"]["end_date"],
                    "n_valid_observations": full_res["timeseries"]["n_valid"],
                    "trend": full_res["trend"],
                    "statistics": full_res["statistics"],
                    "data_source": full_res.get("data_source", src),
                    "data_provenance": full_res.get("data_provenance", provenance)
                }

            elif tool_name == "calculate_trend":
                analysis_id = tool_args["analysis_id"]
                if analysis_id in self._analysis_cache:
                    result = self._analysis_cache[analysis_id].get("trend", {"error": "No trend computed"})
                else:
                    result = {"error": f"Analysis {analysis_id} not found in session. Run extract_regional_timeseries first."}

            elif tool_name == "compare_regions":
                results = {}
                for region_key in ["a", "b"]:
                    df, notes, provenance, src, *extra = self.data_accessor.get_timeseries_data(
                        dataset_id=tool_args["dataset_id"],
                        min_lon=tool_args[f"region_{region_key}_min_lon"],
                        max_lon=tool_args[f"region_{region_key}_max_lon"],
                        min_lat=tool_args[f"region_{region_key}_min_lat"],
                        max_lat=tool_args[f"region_{region_key}_max_lat"],
                        start_date=tool_args["start_date"],
                        end_date=tool_args["end_date"],
                        region_name=tool_args.get(f"region_{region_key}_name"),
                    )
                    info = self.data_accessor.get_dataset_info(tool_args["dataset_id"])
                    full_res = self.analysis_engine.run_full_analysis(
                        df=df,
                        dataset_id=tool_args["dataset_id"],
                        variable=info["variable"],
                        units=info["units"],
                        region_name=tool_args[f"region_{region_key}_name"],
                        source_description=info["description"],
                        processing_notes=notes,
                        data_provenance=provenance,
                        data_source=src
                    )
                    self._analysis_cache[full_res["analysis_id"]] = full_res
                    results[f"region_{region_key}"] = {
                        "analysis_id": full_res["analysis_id"],
                        "region": full_res["timeseries"]["region"],
                        "trend": full_res["trend"],
                        "statistics": full_res["statistics"]
                    }

                result = {
                    "region_a": results["region_a"],
                    "region_b": results["region_b"],
                    "comparison_notes": [
                        "Both regions use the same dataset, units, and temporal resolution.",
                        "Direct comparison is valid within the stated limitations of each analysis."
                    ]
                }

            elif tool_name == "get_analysis_sources":
                analysis_id = tool_args["analysis_id"]
                if analysis_id in self._analysis_cache:
                    cached = self._analysis_cache[analysis_id]
                    result = {
                        "analysis_id": analysis_id,
                        "dataset": cached["timeseries"]["dataset_id"],
                        "source_description": cached["timeseries"]["source_description"],
                        "processing_notes": cached["timeseries"]["processing_notes"],
                        "methodology": cached["methodology"],
                        "computed_at": cached["computed_at"],
                        "citations": [
                            "Huffman, G.J., et al. (2023). GPM IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07. Goddard Earth Sciences Data and Information Services Center (GES DISC). https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07"
                        ]
                    }
                else:
                    result = {"error": f"Analysis {analysis_id} not found"}

            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            self._current_tool_calls.append({
                "tool": tool_name,
                "args": tool_args,
                "success": "error" not in result
            })
            return result

        except Exception as e:
            safe_err = self._sanitize_error(str(e))
            logger.error(f"Tool {tool_name} failed: {safe_err}")
            err_dict = {"error": f"Tool execution failed: {safe_err}"}
            self._current_tool_calls.append({
                "tool": tool_name,
                "args": tool_args,
                "success": False
            })
            return err_dict

    def _get_tools(self) -> List[Any]:
        """Return callable tool functions for Google Gen AI AFC."""
        agent = self

        def get_available_datasets() -> dict:
            """List all available NASA Earth observation datasets in BHIMA with metadata."""
            return agent._execute_tool("get_available_datasets", {})

        def get_dataset_metadata(dataset_id: str) -> dict:
            """Get detailed metadata for a specific dataset including units, resolution, coverage period, and limitations."""
            return agent._execute_tool("get_dataset_metadata", {"dataset_id": dataset_id})

        def extract_regional_timeseries(
            dataset_id: str,
            region_name: str,
            min_lon: float,
            max_lon: float,
            min_lat: float,
            max_lat: float,
            start_date: str,
            end_date: str
        ) -> dict:
            """Extract a time series of observations for a geographical region from a NASA dataset and compute trends."""
            return agent._execute_tool("extract_regional_timeseries", {
                "dataset_id": dataset_id,
                "region_name": region_name,
                "min_lon": min_lon,
                "max_lon": max_lon,
                "min_lat": min_lat,
                "max_lat": max_lat,
                "start_date": start_date,
                "end_date": end_date
            })

        def calculate_trend(analysis_id: str) -> dict:
            """Calculate trend statistics for a previously extracted time series analysis. Returns Sen's slope, p-value, and trend direction."""
            return agent._execute_tool("calculate_trend", {"analysis_id": analysis_id})

        def compare_regions(
            dataset_id: str,
            region_a_name: str,
            region_a_min_lon: float,
            region_a_max_lon: float,
            region_a_min_lat: float,
            region_a_max_lat: float,
            region_b_name: str,
            region_b_min_lon: float,
            region_b_max_lon: float,
            region_b_min_lat: float,
            region_b_max_lat: float,
            start_date: str,
            end_date: str
        ) -> dict:
            """Compare time series and trends between two geographical regions."""
            return agent._execute_tool("compare_regions", {
                "dataset_id": dataset_id,
                "region_a_name": region_a_name,
                "region_a_min_lon": region_a_min_lon,
                "region_a_max_lon": region_a_max_lon,
                "region_a_min_lat": region_a_min_lat,
                "region_a_max_lat": region_a_max_lat,
                "region_b_name": region_b_name,
                "region_b_min_lon": region_b_min_lon,
                "region_b_max_lon": region_b_max_lon,
                "region_b_min_lat": region_b_min_lat,
                "region_b_max_lat": region_b_max_lat,
                "start_date": start_date,
                "end_date": end_date
            })

        def get_analysis_sources(analysis_id: str) -> dict:
            """Get the data sources, methodology, and citation information for a completed analysis."""
            return agent._execute_tool("get_analysis_sources", {"analysis_id": analysis_id})

        return [
            get_available_datasets,
            get_dataset_metadata,
            extract_regional_timeseries,
            calculate_trend,
            compare_regions,
            get_analysis_sources
        ]

    def chat(self, message: str, history: List[Dict] = None) -> Dict[str, Any]:
        """Process a user message with tool calling and automatic fallback across valid models."""
        if not self.has_api_key or self.client is None:
            return self._fallback_response(message)

        # Build candidate models list (primary model + fast lightweight fallbacks)
        candidate_models = [self.model_name]
        for fallback in ["gemini-3.5-flash", "gemini-2.5-flash-lite"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error = ""
        # Build conversation history once
        chat_history = []
        if history:
            for h in history[-10:]:
                content_str = h.get("content", "")
                if not content_str:
                    continue
                role = "user" if h.get("role") == "user" else "model"
                chat_history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=content_str)]
                    )
                )

        # Ensure history does not end with 'user' message as send_message appends the new prompt
        if chat_history and chat_history[-1].role == "user":
            chat_history.pop()

        config = types.GenerateContentConfig(
            system_instruction=self._system_prompt(),
            tools=self._get_tools(),
            temperature=0.2,
        )

        for model_candidate in candidate_models:
            self._current_tool_calls = []
            try:
                chat = self.client.chats.create(
                    model=model_candidate,
                    history=list(chat_history) if chat_history else None,
                    config=config
                )

                response = chat.send_message(message)
                final_text = response.text or ""

                # Check if any analysis was computed and cached during this interaction
                latest_analysis = None
                if self._analysis_cache:
                    latest_analysis = list(self._analysis_cache.values())[-1]

                return {
                    "response": final_text,
                    "tool_calls_made": list(self._current_tool_calls),
                    "analysis_results": latest_analysis,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }

            except Exception as e:
                err_text = str(e)
                safe_err = self._sanitize_error(err_text)
                last_error = safe_err
                logger.warning(f"Model {model_candidate} encountered issue: {safe_err}. Attempting next model...")
                # If it's a quota or transient error (429, 503), try next model
                if any(code in err_text for code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                    continue
                # For other errors, break and report
                break

        logger.error(f"Agent chat failed on all candidate models: {last_error}")
        return {
            "response": f"I encountered an error: {last_error}. Please check backend logs or try again.",
            "tool_calls_made": list(self._current_tool_calls),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

    def _fallback_response(self, message: str) -> Dict[str, Any]:
        """Fallback when Gemini API key is not configured."""
        return {
            "response": (
                "The BHIMA AI agent requires a Gemini API key to function. "
                "Please configure GEMINI_API_KEY in your .env file. "
                "\n\nIn the meantime, you can use the Earth Explorer to investigate regions manually "
                "and view trend analysis results."
            ),
            "tool_calls_made": [],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    Uses Gemini with function calling to invoke real backend analysis tools.
    """

    def __init__(self, api_key: str, data_accessor, analysis_engine):
        self.api_key = api_key
        self.has_api_key = bool(api_key and api_key.strip() and api_key != "your_gemini_key_here")
        self.data_accessor = data_accessor
        self.analysis_engine = analysis_engine
        self._analysis_cache: Dict[str, Any] = {}

        if self.has_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro",
                    system_instruction=self._system_prompt()
                )
                logger.info("Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Gemini setup failed: {e}")
                self.has_api_key = False
                self.model = None
        else:
            logger.warning("Gemini API key not configured. Agent will use fallback mode.")
            self.model = None

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
- Amazon Basin: min_lon=-73.0, max_lon=-50.0, min_lat=-15.0, max_lat=5.0
- Sahel Africa: min_lon=-15.0, max_lon=40.0, min_lat=10.0, max_lat=20.0
- California: min_lon=-124.5, max_lon=-114.1, min_lat=32.5, max_lat=42.0
- Western Australia: min_lon=114.0, max_lon=130.0, min_lat=-35.0, max_lat=-22.0"""

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return structured result."""
        try:
            if tool_name == "get_available_datasets":
                return {"datasets": self.data_accessor.get_all_datasets()}

            elif tool_name == "get_dataset_metadata":
                dataset_id = tool_args["dataset_id"]
                return self.data_accessor.get_dataset_info(dataset_id)

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
                result = self.analysis_engine.run_full_analysis(
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
                # Cache for follow-up tool calls
                self._analysis_cache[result["analysis_id"]] = result
                return result

            elif tool_name == "calculate_trend":
                analysis_id = tool_args["analysis_id"]
                if analysis_id in self._analysis_cache:
                    return self._analysis_cache[analysis_id].get("trend", {"error": "No trend computed"})
                return {"error": f"Analysis {analysis_id} not found in session. Run extract_regional_timeseries first."}

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
                    result = self.analysis_engine.run_full_analysis(
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
                    self._analysis_cache[result["analysis_id"]] = result
                    results[f"region_{region_key}"] = result

                return {
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
                    return {
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
                return {"error": f"Analysis {analysis_id} not found"}

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": f"Tool execution failed: {str(e)}"}

    def chat(self, message: str, history: List[Dict] = None) -> Dict[str, Any]:
        """Process a user message with tool calling."""
        if not self.has_api_key or self.model is None:
            return self._fallback_response(message)

        try:
            import google.generativeai as genai
            from google.generativeai.types import FunctionDeclaration, Tool

            # Build Gemini tools from definitions
            gemini_tools = []
            for tool_def in TOOL_DEFINITIONS:
                decl = FunctionDeclaration(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    parameters=tool_def["parameters"]
                )
                gemini_tools.append(decl)

            tool_obj = Tool(function_declarations=gemini_tools)

            # Build conversation history
            chat_history = []
            if history:
                for h in history[-10:]:  # last 10 messages
                    role = "user" if h["role"] == "user" else "model"
                    chat_history.append({"role": role, "parts": [h["content"]]})

            chat = self.model.start_chat(history=chat_history)

            tool_calls_made = []
            response = chat.send_message(message, tools=[tool_obj])

            # Agentic tool calling loop
            max_turns = 5
            turns = 0
            while turns < max_turns:
                turns += 1

                # Check for function calls
                fc = None
                try:
                    fc = response.candidates[0].content.parts[0].function_call
                except (IndexError, AttributeError):
                    break

                if not fc or not fc.name:
                    break

                # Execute the tool
                tool_name = fc.name
                tool_args = dict(fc.args)
                tool_result = self._execute_tool(tool_name, tool_args)

                tool_calls_made.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "success": "error" not in tool_result
                })

                # Send tool result back
                import google.generativeai.protos as protos
                tool_response = protos.Part(
                    function_response=protos.FunctionResponse(
                        name=tool_name,
                        response={"result": json.dumps(tool_result, default=str)[:8000]}
                    )
                )
                response = chat.send_message(tool_response)

            # Extract final text response
            final_text = ""
            try:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text += part.text
            except Exception:
                final_text = "I encountered an issue generating a response. Please try again."

            return {
                "response": final_text,
                "tool_calls_made": tool_calls_made,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

        except Exception as e:
            logger.error(f"Agent chat failed: {e}")
            return {
                "response": f"I encountered an error: {str(e)}. Please check the server logs.",
                "tool_calls_made": [],
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

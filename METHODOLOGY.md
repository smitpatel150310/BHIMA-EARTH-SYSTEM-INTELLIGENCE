# BHIMA Scientific Methodology

## 1. Regional Extraction & Spatial Averaging

For any user-specified bounding box defined by $[\lambda_{\min}, \lambda_{\max}] \times [\phi_{\min}, \phi_{\max}]$, the regional mean observation for time step $t$ is computed as the arithmetic mean of all unmasked grid cells falling within the coordinates:

$$\bar{X}_t = \frac{1}{N_{\text{valid}}} \sum_{i=1}^{N_{\text{valid}}} X_{i, t}$$

Where:
- $X_{i, t}$ is the satellite pixel value at spatial coordinate $i$ and month $t$.
- $N_{\text{valid}}$ is the count of non-fill pixels (omitting values $\le -9999.0$).
- Spatial coverage fraction is reported as $C_t = \frac{N_{\text{valid}}}{N_{\text{total}}}$.

---

## 2. Trend Detection Framework

Environmental time series routinely violate ordinary least squares (OLS) regression assumptions due to non-normal errors, strong seasonality, and autocorrelation. BHIMA employs robust, non-parametric statistical procedures.

### Hamed & Rao (1998) Modified Mann-Kendall Test
The standard Mann-Kendall statistic $S$ is defined as:

$$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \operatorname{sgn}(X_j - X_k)$$

Where:
$$\operatorname{sgn}(\theta) = \begin{cases} 1 & \text{if } \theta > 0 \\ 0 & \text{if } \theta = 0 \\ -1 & \text{if } \theta < 0 \end{cases}$$

Under serial correlation, the variance $\operatorname{Var}(S)$ is underestimated, inflating Type I error rates. The Hamed & Rao modification computes an effective sample size correction factor $\frac{n}{n^*}$:

$$\operatorname{Var}^*(S) = \operatorname{Var}(S) \times \frac{n}{n^*}$$

$$\frac{n}{n^*} = 1 + \frac{2}{n(n-1)(n-2)} \sum_{i=1}^{n-1} (n - i)(n - i - 1)(n - i - 2) \rho_S(i)$$

Where $\rho_S(i)$ is the rank autocorrelation function of the series. The standard test statistic $Z$ is evaluated against standard normal critical values at $\alpha = 0.05$.

### Sen's Non-Parametric Slope Estimator
The rate of change is quantified using the median of all pairwise slopes:

$$Q_k = \frac{X_j - X_i}{j - i} \quad \text{for } 1 \le i < j \le n$$

$$\beta = \operatorname{median}(Q_k)$$

Annualized slope is reported as $\beta_{\text{annual}} = 12 \times \beta$.

### Uncertainty Bounds
Sen's slope confidence intervals are computed using non-parametric percentile bootstrapping ($B = 500$ resamples) to generate empirical 95% confidence intervals:

$$\operatorname{CI}_{0.95} = [Q_{0.025}^*, Q_{0.975}^*]$$

---

## 3. Data Integrity & Disclosures

1. **Minimum Sample Size**: A minimum of 10 valid monthly observations is enforced before attempting statistical trend tests.
2. **Missing Value Handling**: Missing months are cataloged and explicitly recorded in output metadata rather than naively interpolated.
3. **Correlation vs. Causation**: BHIMA explicitly isolates empirical trend detection from causal attribution.

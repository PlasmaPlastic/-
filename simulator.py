
import math
R_EARTH_KM = 6371.0
MU_KM3_S2 = 398600.4418
SIGMA = 5.670374419e-8
T_SPACE = 3.0
CELL_TYPES = {
    "III-V_3J": {"eta0": 0.30, "beta": 0.0020},
    "Si": {"eta0": 0.22, "beta": 0.0045},
    "GaAs": {"eta0": 0.28, "beta": 0.0025},
    "Perovskite": {"eta0": 0.25, "beta": 0.0035},
}
def orbital_period_seconds(altitude_km: float) -> float:
    r = R_EARTH_KM + altitude_km
    return 2 * math.pi * math.sqrt(r**3 / MU_KM3_S2)
def is_eclipse(orbital_phase_deg: float, altitude_km: float) -> bool:
    r = R_EARTH_KM + altitude_km
    shadow_angle = math.degrees(math.asin(R_EARTH_KM / r))
    phase = orbital_phase_deg % 360
    return abs((phase - 180) % 360) < shadow_angle
def solar_incidence_cos(orbital_phase_deg: float, panel_orientation_deg: float, inclination_deg: float) -> float:
    total_angle = math.radians(orbital_phase_deg + panel_orientation_deg)
    inc_factor = math.cos(math.radians(inclination_deg)) * 0.3 + 0.7
    cos_theta = math.cos(total_angle) * inc_factor
    return max(0.0, cos_theta)
def thermal_temperature_K(irradiance_W: float, cos_theta: float, absorptivity: float, emissivity: float) -> float:
    if cos_theta <= 0 or irradiance_W <= 0:
        return 280.0
    absorbed = absorptivity * irradiance_W * cos_theta
    T4 = absorbed / (emissivity * SIGMA) + T_SPACE**4
    T = T4 ** 0.25
    return min(max(T, 200.0), 450.0)
def radiation_dose_rate(altitude_km: float, inclination_deg: float) -> float:
    alt_factor = (altitude_km / 500.0) ** 1.2
    inc_factor = 1.0 + 0.8 * math.sin(math.radians(inclination_deg))
    return 0.01 * alt_factor * inc_factor
def degraded_efficiency(eta0: float, beta: float, T_K: float, dose: float, time_years: float) -> float:
    eta_temp = eta0 * (1 - beta * (T_K - 298.15))
    k = 0.05
    eta_rad = eta_temp * math.exp(-k * dose * time_years)
    return max(0.05, eta_rad)
def simulate(config: dict):
    alt = config.get("altitude_km", 500.0)
    inc = config.get("inclination_deg", 45.0)
    raan = config.get("raan_deg", 0.0)
    init_phase = config.get("initial_orbital_phase_deg", 0.0)
    panel_ori = config.get("panel_orientation_deg", 0.0)
    area = config.get("panel_area_m2", 20.0)
    cell_type = config.get("solar_cell_type", "III-V_3J")
    I0 = config.get("solar_irradiance_W_m2", 1361.0)
    absorp = config.get("absorptivity", 0.90)
    emiss = config.get("emissivity", 0.85)
    dur_days = config.get("simulation_duration_days", 1.0)
    dt = config.get("time_step_seconds", 60.0)
    cell = CELL_TYPES.get(cell_type, CELL_TYPES["III-V_3J"])
    eta0 = cell["eta0"]
    beta = cell["beta"]
    period = orbital_period_seconds(alt)
    total_seconds = dur_days * 86400.0
    steps = int(total_seconds // dt)
    dose_rate = radiation_dose_rate(alt, inc)
    cumulative_dose = 0.0
    timeseries = []
    total_energy_Wh = 0.0
    max_power = 0.0
    power_sum = 0.0
    temp_sum = 0.0
    eta_sum = 0.0
    eta = eta0
    for i in range(steps):
        t_sec = i * dt
        t_days = t_sec / 86400.0
        t_years = t_days / 365.25
        orbital_phase = (init_phase + (t_sec / period) * 360.0 + raan) % 360.0
        eclipse = is_eclipse(orbital_phase, alt)
        cos_theta = 0.0 if eclipse else solar_incidence_cos(orbital_phase, panel_ori, inc)
        T_K = thermal_temperature_K(I0, cos_theta, absorp, emiss)
        cumulative_dose += dose_rate * (dt / 86400.0)
        eta = degraded_efficiency(eta0, beta, T_K, cumulative_dose, t_years)
        P_out = 0.0 if eclipse else eta * I0 * area * cos_theta
        total_energy_Wh += P_out * (dt / 3600.0)
        max_power = max(max_power, P_out)
        power_sum += P_out
        temp_sum += T_K
        eta_sum += eta
        if i % 10 == 0 or steps < 1000:
            timeseries.append({
                "time_sec": t_sec,
                "time_days": round(t_days, 4),
                "orbital_phase_deg": round(orbital_phase, 2),
                "eclipse": eclipse,
                "cos_theta": round(cos_theta, 4),
                "temperature_K": round(T_K, 2),
                "efficiency": round(eta, 4),
                "power_W": round(P_out, 2),
                "dose": round(cumulative_dose, 4)
            })
    avg_power = power_sum / steps if steps else 0
    summary = {
        "altitude_km": alt,
        "inclination_deg": inc,
        "raan_deg": raan,
        "initial_orbital_phase_deg": init_phase,
        "panel_orientation_deg": panel_ori,
        "panel_area_m2": area,
        "solar_cell_type": cell_type,
        "orbital_period_s": round(period, 1),
        "max_power_W": round(max_power, 2),
        "avg_power_W": round(avg_power, 2),
        "total_energy_kWh": round(total_energy_Wh / 1000.0, 2),
        "total_energy_Wh": round(total_energy_Wh, 2),
        "avg_temperature_K": round(temp_sum / steps if steps else 0, 2),
        "avg_efficiency": round(eta_sum / steps if steps else 0, 4),
        "final_efficiency": round(eta, 4),
        "final_dose": round(cumulative_dose, 4),
        "steps": steps,
        "duration_days": dur_days
    }
    return timeseries, summary
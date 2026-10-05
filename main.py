
import os
from datetime import datetime
from simulator import simulate
DEFAULT_CONFIG = {
    "altitude_km": 500.0,
    "inclination_deg": 45.0,
    "raan_deg": 0.0,
    "initial_orbital_phase_deg": 0.0,
    "panel_orientation_deg": 0.0,
    "panel_area_m2": 20.0,
    "solar_cell_type": "III-V_3J",
    "solar_irradiance_W_m2": 1361.0,
    "absorptivity": 0.90,
    "emissivity": 0.85,
    "simulation_duration_days": 1.0,
    "time_step_seconds": 60.0,
    "electricity_price_usd_per_kwh": 0.15,
    "lifetime_years": 10.0
}
SERIAL_FILE = "results/serial_counter.txt"
def get_next_serial(prefix="SIM"):
    os.makedirs("results", exist_ok=True)
    counter = 0
    if os.path.exists(SERIAL_FILE):
        try:
            with open(SERIAL_FILE, 'r') as f:
                counter = int(f.read().strip() or 0)
        except:
            counter = 0
    counter += 1
    with open(SERIAL_FILE, 'w') as f:
        f.write(str(counter))
    return f"{prefix}-{counter:06d}"
def to_txt_simulation_timeseries(serial, timeseries):
    lines = [f"{serial}", "="*40, "[TIMESERIES]", "time_days,phase_deg,eclipse,cos_theta,temp_K,eff,power_W,dose"]
    for row in timeseries:
        lines.append(f"{row['time_days']},{row['orbital_phase_deg']},{int(row['eclipse'])},{row['cos_theta']},{row['temperature_K']},{row['efficiency']},{row['power_W']},{row['dose']}")
    return "\n".join(lines)
def to_txt_simulation_result(serial, config, summary):
    now = datetime.now().isoformat()
    lines = [f"{serial}", "="*40, f"generated_at: {now}", "", "[INPUT]"]
    for k,v in config.items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("[SUMMARY]")
    for k,v in summary.items():
        lines.append(f"{k}: {v}")
    w1, w2, w3, w4 = 1.0, 0.01, 10.0, 0.1
    score = w1*summary.get('avg_power_W',0) - w2*summary.get('avg_temperature_K',0) - w3*summary.get('final_dose',0) + w4*summary.get('total_energy_kWh',0)
    lines.append(f"score: {round(score,2)}")
    return "\n".join(lines)
def run_single_simulation(custom_config=None, save=True):
    config = {**DEFAULT_CONFIG, **(custom_config or {})}
    serial = get_next_serial("SIM")
    timeseries, summary = simulate(config)
    if save:
        os.makedirs("results", exist_ok=True)
        with open(f"results/simulation_timeseries_{serial}.txt", 'w', encoding='utf-8') as f:
            f.write(to_txt_simulation_timeseries(serial, timeseries))
        with open(f"results/simulation_result_{serial}.txt", 'w', encoding='utf-8') as f:
            f.write(to_txt_simulation_result(serial, config, summary))
        with open("results/simulation_timeseries.txt", 'w', encoding='utf-8') as f:
            f.write(to_txt_simulation_timeseries(serial, timeseries))
        with open("results/simulation_result.txt", 'w', encoding='utf-8') as f:
            f.write(to_txt_simulation_result(serial, config, summary))
    print(f"[{serial}] 완료 - 평균 {summary['avg_power_W']} W, 총 {summary['total_energy_kWh']} kWh")
    return serial, timeseries, summary
if __name__ == "__main__":
    run_single_simulation()
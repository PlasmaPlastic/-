
import math, random, itertools
from simulator import simulate
from main import get_next_serial
def generate_grid(ranges):
    keys = list(ranges.keys())
    values_list = []
    for k in keys:
        r = ranges[k]
        min_v, max_v, step = r
        vals = []
        v = min_v
        while v <= max_v + 1e-9:
            vals.append(round(v, 2))
            v += step
        values_list.append(vals)
    for combo in itertools.product(*values_list):
        yield dict(zip(keys, combo))
def score_summary(summary, weights=None):
    w = weights or {"w1":1.0, "w2":0.01, "w3":10.0, "w4":0.1}
    return w["w1"]*summary["avg_power_W"] - w["w2"]*summary["avg_temperature_K"] - w["w3"]*summary["final_dose"] + w["w4"]*summary["total_energy_kWh"]
def optimize_brute_force(base_config, ranges, max_cases=20000):
    tested=[]; best=None; best_cfg=None; best_score=-1e18
    for idx, var_cfg in enumerate(generate_grid(ranges)):
        if idx >= max_cases: break
        cfg = {**base_config, **var_cfg}
        _, summary = simulate(cfg)
        sc = score_summary(summary)
        rec = {"case_serial": f"CASE-{idx+1:06d}", "config": var_cfg, "summary": summary, "score": round(sc,2)}
        tested.append(rec)
        if sc > best_score:
            best_score=sc; best=rec; best_cfg=cfg
    return tested, best, best_cfg
def optimize_random(base_config, ranges, n=300):
    tested=[]; best=None; best_cfg=None; best_score=-1e18
    keys=list(ranges.keys())
    for i in range(n):
        var_cfg={}
        for k in keys:
            mn,mx,_ = ranges[k]
            var_cfg[k]= round(random.uniform(mn,mx),2)
        cfg={**base_config, **var_cfg}
        _, summary = simulate(cfg)
        sc=score_summary(summary)
        rec={"case_serial": f"CASE-{i+1:06d}", "config": var_cfg, "summary": summary, "score": round(sc,2)}
        tested.append(rec)
        if sc>best_score:
            best_score=sc; best=rec; best_cfg=cfg
    return tested, best, best_cfg
def optimize_genetic(base_config, ranges, pop=30, gens=30):
    keys=list(ranges.keys())
    def random_cfg():
        return {k: round(random.uniform(ranges[k][0], ranges[k][1]),2) for k in keys}
    def crossover(a,b):
        return {k: a[k] if random.random()<0.5 else b[k] for k in keys}
    def mutate(cfg):
        nk=dict(cfg)
        k=random.choice(keys)
        mn,mx,_=ranges[k]
        nk[k]= max(mn, min(mx, nk[k]+ random.uniform(-5,5)))
        nk[k]=round(nk[k],2)
        return nk
    population=[random_cfg() for _ in range(pop)]
    tested=[]; best=None; best_cfg=None; best_score=-1e18; case_id=0
    for gen in range(gens):
        scored=[]
        for cfg_var in population:
            case_id+=1
            cfg={**base_config, **cfg_var}
            _, summary = simulate(cfg)
            sc=score_summary(summary)
            rec={"case_serial": f"CASE-{case_id:06d}", "config": cfg_var, "summary": summary, "score": round(sc,2), "gen": gen}
            tested.append(rec)
            scored.append((sc, cfg_var, rec))
            if sc>best_score:
                best_score=sc; best=rec; best_cfg=cfg
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s[1] for s in scored[:pop//2]]
        new_pop=[]
        while len(new_pop)<pop:
            p1,p2=random.sample(top,2)
            child=crossover(p1,p2)
            if random.random()<0.3:
                child=mutate(child)
            new_pop.append(child)
        population=new_pop
    return tested, best, best_cfg
def optimize_pso(base_config, ranges, particles=30, iters=30):
    keys=list(ranges.keys())
    pos=[{k: random.uniform(ranges[k][0], ranges[k][1]) for k in keys} for _ in range(particles)]
    vel=[{k: random.uniform(-1,1) for k in keys} for _ in range(particles)]
    pbest=pos[:]
    pbest_score=[-1e18]*particles
    gbest=None; gbest_score=-1e18; gbest_cfg=None; tested=[]; case_id=0; best=None
    for it in range(iters):
        for i in range(particles):
            cfg={**base_config, **{k: round(pos[i][k],2) for k in keys}}
            _, summary = simulate(cfg)
            sc=score_summary(summary)
            case_id+=1
            rec={"case_serial": f"CASE-{case_id:06d}", "config": {k: round(pos[i][k],2) for k in keys}, "summary": summary, "score": round(sc,2), "iter": it}
            tested.append(rec)
            if sc>pbest_score[i]:
                pbest_score[i]=sc; pbest[i]=pos[i].copy()
            if sc>gbest_score:
                gbest_score=sc; gbest=pos[i].copy(); gbest_cfg=cfg; best=rec
        for i in range(particles):
            for k in keys:
                r1,r2=random.random(), random.random()
                vel[i][k]= 0.5*vel[i][k] + 1.5*r1*(pbest[i][k]-pos[i][k]) + 1.5*r2*(gbest[k]-pos[i][k])
                pos[i][k]+=vel[i][k]
                mn,mx,_=ranges[k]
                pos[i][k]= max(mn, min(mx, pos[i][k]))
    return tested, best, gbest_cfg
def optimize_bayesian(base_config, ranges, n_init=20, n_iter=30):
    tested, best, best_cfg = optimize_random(base_config, ranges, n=n_init)
    if not best:
        return tested,best,best_cfg
    best_score=best["score"]
    keys=list(ranges.keys())
    case_id=len(tested)
    for _ in range(n_iter):
        var_cfg={}
        for k in keys:
            mn,mx,_=ranges[k]
            center=best["config"][k]
            var_cfg[k]= round(max(mn, min(mx, random.gauss(center, (mx-mn)*0.1))),2)
        cfg={**base_config, **var_cfg}
        _, summary = simulate(cfg)
        sc=score_summary(summary)
        case_id+=1
        rec={"case_serial": f"CASE-{case_id:06d}", "config": var_cfg, "summary": summary, "score": round(sc,2)}
        tested.append(rec)
        if sc>best_score:
            best_score=sc; best=rec; best_cfg=cfg
    return tested, best, best_cfg
ALGORITHMS = {
    "brute_force": optimize_brute_force,
    "grid_search": optimize_brute_force,
    "random_search": optimize_random,
    "genetic": optimize_genetic,
    "pso": optimize_pso,
    "bayesian": optimize_bayesian,
    "gradient": optimize_random,
    "ai_based": optimize_bayesian
}
def run_optimization(base_config, ranges, algorithm="grid_search", max_cases=5000, save=True):
    serial = get_next_serial("OPT")
    algo_fn = ALGORITHMS.get(algorithm, optimize_brute_force)
    if algorithm in ["brute_force","grid_search"]:
        tested, best, best_cfg = algo_fn(base_config, ranges, max_cases=max_cases)
    elif algorithm == "random_search":
        tested, best, best_cfg = algo_fn(base_config, ranges, n=min(max_cases, 500))
    elif algorithm == "genetic":
        tested, best, best_cfg = algo_fn(base_config, ranges, pop=20, gens=20)
    elif algorithm == "pso":
        tested, best, best_cfg = algo_fn(base_config, ranges, particles=20, iters=20)
    else:
        tested, best, best_cfg = algo_fn(base_config, ranges)
    if save:
        import os
        os.makedirs("results", exist_ok=True)
        lines=[f"{serial}", "="*50, f"algorithm: {algorithm}", f"tested_count: {len(tested)}", "", "[OPTIMIZATION_INPUT]"]
        lines.append(f"base_config: {base_config}")
        lines.append(f"ranges: {ranges}")
        lines.append("")
        lines.append("[BEST_SOLUTION]")
        if best:
            lines.append(f"score: {best['score']}")
            lines.append(f"config: {best['config']}")
            lines.append(f"summary: {best['summary']}")
        lines.append("")
        lines.append("[TESTED_SUMMARY]")
        for rec in tested[:200]:
            lines.append(f"{rec['case_serial']}: score={rec['score']}, power={rec['summary']['avg_power_W']}W, energy={rec['summary']['total_energy_kWh']}kWh, config={rec['config']}")
        txt="\n".join(lines)
        with open(f"results/optimization_result_{serial}.txt", 'w', encoding='utf-8') as f:
            f.write(txt)
        with open("results/optimization_result.txt", 'w', encoding='utf-8') as f:
            f.write(txt)
    print(f"[{serial}] 최적화 완료 - {algorithm}, {len(tested)} cases")
    return serial, tested, best, best_cfg
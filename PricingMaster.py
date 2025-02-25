import streamlit as st
import itertools
import random
import matplotlib.pyplot as plt

# -------------------------------
# Funciones de la lógica del negocio (Mejoradas)
# -------------------------------

def generate_candidate_prices(global_min, global_max, scenario):
    num_candidates = 9
    if global_max == global_min:
        return [global_min]
    
    step = (global_max - global_min) / (num_candidates - 1)
    candidates = [round(global_min + i * step, 2) for i in range(num_candidates)]
    
    if scenario == "alta":
        subset = candidates[6:]  # Últimos 3 candidatos
    elif scenario == "moderada":
        subset = candidates[3:6]  # 3 centrales
    elif scenario == "baja":
        subset = candidates[:3]   # Primeros 3
    else:
        subset = candidates
    return subset

def generate_combinations(sections, scenario, global_min, global_max, margin_factor):
    def get_candidates(i):
        return generate_candidate_prices(global_min, global_max, scenario)
    
    candidate_lists = [get_candidates(i) for i in range(len(sections))]
    valid_combos = []
    
    for combo in itertools.islice(itertools.product(*candidate_lists), 100_000):
        if all(combo[j] >= margin_factor * combo[j+1] for j in range(len(combo)-1)):
            valid_combos.append(combo)
    
    return valid_combos

def compute_revenue_for_combo(combo, sections, scenario):
    sell_rates = {"alta": 0.98, "moderada": 0.90, "baja": 0.85}
    sell_rate = sell_rates.get(scenario, 0.95)
    return sum(sec['seats'] * sell_rate * price for price, sec in zip(combo, sections))

def heuristic_search(target, sections, global_min, global_max, margin_factor):
    best_combo = None
    best_diff = float('inf')
    
    for _ in range(10_000):
        combo = []
        prev_price = global_max
        for _ in sections:
            price = random.uniform(global_min, prev_price / margin_factor)
            combo.append(round(price, 2))
            prev_price = price
        
        if all(combo[i] >= margin_factor * combo[i+1] for i in range(len(combo)-1)):
            revenue = compute_revenue_for_combo(combo, sections, "alta")
            diff = abs(revenue - target)
            if diff < best_diff:
                best_combo, best_diff = combo, diff
    
    return best_combo

# -------------------------------
# Interfaz de Usuario
# -------------------------------

def main():
    st.title("🚀 Optimizador de Precios para Eventos (Versión Mejorada)")
    
    # Parámetros principales
    target = st.sidebar.number_input("Objetivo de Ingreso ($)", min_value=1000.0, value=100_000.0)
    num_sections = st.sidebar.number_input("Número de Secciones", 1, 10, 3)
    margin = st.sidebar.slider("Margen Mínimo entre Secciones (%)", 2, 15, 5)
    margin_factor = 1 + (margin / 100)
    
    # Configurar secciones
    sections = []
    for i in range(num_sections):
        with st.expander(f"Sección {i+1}"):
            name = st.text_input(f"Nombre", value=f"Sección {i+1}", key=f"name_{i}")
            seats = st.number_input("Asientos", 10, 10_000, 500, key=f"seats_{i}")
            sections.append({'name': name, 'seats': seats})
    
    # Rango de precios
    st.sidebar.subheader("Rango de Precios")
    global_min = st.sidebar.number_input("Mínimo ($)", value=50.0)
    global_max = st.sidebar.number_input("Máximo ($)", value=200.0, min_value=global_min + 0.01)
    
    if st.button("🔍 Buscar Combinaciones Óptimas"):
        scenarios = {"Alta Demanda": "alta", "Moderada": "moderada", "Baja": "baja"}
        
        for scenario_name, scenario_code in scenarios.items():
            st.subheader(f"Escenario: {scenario_name}")
            
            # Intento 1: Búsqueda tradicional
            combos = generate_combinations(sections, scenario_code, global_min, global_max, margin_factor)
            
            # Intento 2: Búsqueda heurística si falla el primero
            if not combos:
                st.warning("Usando algoritmo de aproximación...")
                best_combo = heuristic_search(target, sections, global_min, global_max, margin_factor)
                if best_combo:
                    revenue = compute_revenue_for_combo(best_combo, sections, scenario_code)
                    st.success(f"Mejor combinación encontrada: {best_combo}")
                    st.metric("Ingreso Estimado", f"${revenue:,.2f}", delta=f"${revenue - target:,.2f} vs Objetivo")
            
            # ... (procesar y mostrar resultados)

if __name__ == "__main__":
    main()
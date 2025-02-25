import streamlit as st
import itertools
import random
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO

# -------------------------------
# Funciones Nucleares Modificadas
# -------------------------------

def generate_candidate_prices(global_min, global_max, scenario):
    """Genera precios candidatos adaptados al escenario entre min y max."""
    num_candidates = 9
    if global_max <= global_min:
        return [global_min]
    
    step = (global_max - global_min) / (num_candidates - 1)
    candidates = [round(global_min + i * step, 2) for i in range(num_candidates)]
    
    scenario_ranges = {
        "alta": candidates[6:],    # Top 33% del rango
        "moderada": candidates[3:6],  # Rango medio
        "baja": candidates[:3]     # Precios bajos
    }
    return scenario_ranges.get(scenario, candidates)

def generate_valid_combinations(sections, scenario, global_min, global_max, margin_factor):
    """Genera combinaciones con primera y última sección fijas."""
    candidates = []
    for i, _ in enumerate(sections):
        if i == 0:  # Primera sección = precio máximo
            sec_candidates = [round(global_max, 2)]
        elif i == len(sections)-1:  # Última sección = precio mínimo
            sec_candidates = [round(global_min, 2)]
        else:  # Secciones intermedias
            sec_candidates = generate_candidate_prices(global_min, global_max, scenario)
        candidates.append(sec_candidates)
    
    valid = []
    for combo in itertools.islice(itertools.product(*candidates), 100_000):
        if all(combo[i] >= margin_factor * combo[i+1] for i in range(len(combo)-1)):
            valid.append(combo)
    return valid

def heuristic_price_search(target, sections, global_min, global_max, margin_factor, scenario):
    """Búsqueda heurística con extremos fijos."""
    best_combo, best_diff = None, float('inf')
    sell_rates = {"alta": 0.98, "moderada": 0.90, "baja": 0.85}
    
    for _ in range(10_000):
        combo = [round(global_max, 2)]  # Fijar primera sección
        prev_price = global_max
        
        # Generar secciones intermedias
        for _ in range(len(sections)-2):
            min_price = max(global_min, prev_price / margin_factor * 0.95)
            max_price = prev_price / margin_factor
            price = random.uniform(min_price, max_price)
            combo.append(round(price, 2))
            prev_price = price
        
        combo.append(round(global_min, 2))  # Fijar última sección
        
        if all(combo[i] >= margin_factor * combo[i+1] for i in range(len(combo)-1)):
            revenue = sum(
                sec['seats'] * sell_rates.get(scenario, 0.95) * price 
                for price, sec in zip(combo, sections)
            )
            if abs(revenue - target) < best_diff:
                best_combo, best_diff = combo, abs(revenue - target)
    
    return best_combo

# -------------------------------
# Resto del código sin cambios
# -------------------------------

def generate_excel_report(results):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for scenario_name, data in results.items():
            df = pd.DataFrame({
                'Sección': [sec['name'] for sec in data['sections']],
                'Precio Recomendado': data['best_combo'],
                'Asientos Disponibles': [sec['seats'] for sec in data['sections']],
                'Tasa de Venta': [data['sell_rate']] * len(data['sections']),
                'Asientos Vendidos': [int(sec['seats'] * data['sell_rate']) for sec in data['sections']],
                'Ingreso por Sección': [p * s * data['sell_rate'] for p, s in zip(
                    data['best_combo'], 
                    [sec['seats'] for sec in data['sections']]
                )]
            })
            df.to_excel(writer, sheet_name=scenario_name[:31], index=False)
            
            workbook = writer.book
            money_format = workbook.add_format({'num_format': '$#,##0.00'})
            percent_format = workbook.add_format({'num_format': '0.00%'})
            worksheet = writer.sheets[scenario_name[:31]]
            
            worksheet.set_column('A:A', 20)
            worksheet.set_column('B:B', 15, money_format)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 12, percent_format)
            worksheet.set_column('E:E', 15)
            worksheet.set_column('F:F', 15, money_format)
            
    output.seek(0)
    return output

def plot_revenue_analysis(scenario_name, top_combos, sections):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    for idx, combo in enumerate(top_combos, 1):
        ax1.plot([sec['name'] for sec in sections], combo, marker='o', label=f'Combo {idx}')
    ax1.set_title(f"Estrategia de Precios - {scenario_name}")
    ax1.set_ylabel("Precio (USD)")
    ax1.grid(True)
    
    for combo in top_combos:
        margins = [(combo[i] - combo[i+1])/combo[i] for i in range(len(combo)-1)]
        ax2.plot(margins, marker='x', linestyle='--')
    ax2.set_title("Margen entre Secciones")
    ax2.set_ylabel("Porcentaje")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))
    ax2.grid(True)
    
    plt.tight_layout()
    return fig

def main():
    st.set_page_config(page_title="Optimizador de Eventos", layout="wide")
    st.title("🎟️ Optimizador de Precios para Eventos")
    
    with st.sidebar:
        st.header("⚙️ Configuración Global")
        target = st.number_input("Ingreso Objetivo (USD)", min_value=1000.0, value=50000.0, step=1000.0)
        num_sections = st.number_input("Número de Secciones", min_value=2, value=3, step=1)
        margin = st.slider("Margen Mínimo entre Secciones (%)", 2, 20, 5)
        global_min = st.number_input("Precio Mínimo (USD)", value=50.0)
        global_max = st.number_input("Precio Máximo (USD)", value=500.0, min_value=global_min + 0.01)
    
    sections = []
    st.header("📋 Configuración de Secciones")
    
    for i in range(num_sections):
        with st.expander(f"Sección {i+1}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(f"Nombre", value=f"Sección {i+1}", key=f"name_{i}")
            with col2:
                seats = st.number_input("Asientos", 100, 10000, 500, key=f"seats_{i}")
            sections.append({'name': name, 'seats': seats})
    
    report_data = {}
    if st.button("🚀 Optimizar Precios", use_container_width=True):
        margin_factor = 1 + (margin / 100)
        scenarios = {
            "Alta Demanda": "alta",
            "Demanda Media": "moderada", 
            "Baja Demanda": "baja"
        }
        
        for scenario_name, scenario_code in scenarios.items():
            with st.expander(f"📊 {scenario_name}", expanded=True):
                combos = generate_valid_combinations(
                    sections, scenario_code, 
                    global_min, global_max, margin_factor
                )
                
                if not combos:
                    st.warning("Usando algoritmo avanzado de aproximación...")
                    best_combo = heuristic_price_search(
                        target, sections, global_min, 
                        global_max, margin_factor, scenario_code
                    )
                    combos = [best_combo] if best_combo else []
                
                if combos:
                    top_combos = sorted(
                        combos, 
                        key=lambda x: abs(sum(p * s['seats'] * 0.95 for p, s in zip(x, sections)) - target)
                    )[:3]
                    
                    st.pyplot(plot_revenue_analysis(scenario_name, top_combos, sections))
                    
                    sell_rate = {"alta": 0.98, "moderada": 0.90, "baja": 0.85}[scenario_code]
                    report_data[scenario_name] = {
                        'best_combo': top_combos[0],
                        'sell_rate': sell_rate,
                        'sections': sections,
                        'total_revenue': sum(
                            p * s['seats'] * sell_rate 
                            for p, s in zip(top_combos[0], sections)
                        )
                    }
                    
                    for idx, combo in enumerate(top_combos, 1):
                        revenue = sum(p * s['seats'] * sell_rate for p, s in zip(combo, sections))
                        st.subheader(f"Opción {idx}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Ingreso Estimado", f"${revenue:,.2f}", delta=f"${revenue - target:,.2f}")
                        with col2:
                            st.write("Precios por sección:")
                            st.code(" | ".join(f"${p:.2f}" for p in combo))
                else:
                    st.error("No se encontraron combinaciones válidas. Ajuste los parámetros.")

        if report_data:
            excel_file = generate_excel_report(report_data)
            st.success("✅ Optimización completada - Descargue su reporte final")
            st.download_button(
                label="📥 Descargar Reporte Completo (Excel)",
                data=excel_file,
                file_name=f"Reporte_Precios_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
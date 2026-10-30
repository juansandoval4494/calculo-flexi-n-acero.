"""
Aplicación Web Interactiva para Diseño de Vigas de Acero a Flexión
Normativa: AISC 360-16 / AISC 2005 - LRFD (Manual AHMSA Cap. II.2.6)
Sistemas: Inglés (US) y Métrico (SI)
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Agregar carpeta src al path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
from src.engine import SteelBeamDesigner

st.set_page_config(
    page_title="SteelBeam Designer - AISC LRFD",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar catálogo de perfiles
@st.cache_data
def load_profiles():
    csv_path = os.path.join(current_dir, 'data', 'profiles.csv')
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    else:
        # Generar catálogo si no existe
        from src.catalog_builder import create_ahmsa_database
        return create_ahmsa_database()

df_profiles = load_profiles()
designer = SteelBeamDesigner()

# ----------------- BARRA LATERAL (CONFIGURACIÓN) -----------------
st.sidebar.title("⚙️ Parámetros de Diseño")
unit_system = st.sidebar.radio(
    "Sistema de Unidades:",
    options=["Inglés (US: ft, in, kip, ksi)", "Métrico (SI: m, cm, ton, kg/cm²)"],
    index=0
)
is_us = (unit_system == "Inglés (US: ft, in, kip, ksi)")
unit_code = "US" if is_us else "SI"

st.sidebar.markdown("---")
st.sidebar.subheader("🔩 Material (Acero Estructural)")

if is_us:
    steel_grade = st.sidebar.selectbox("Tipo de Acero:", ["A992 / A572 Gr. 50 (Fy = 50 ksi)", "A36 (Fy = 36 ksi)", "Personalizado"])
    if "50" in steel_grade:
        Fy = 50.0
        E = 29000.0
    elif "36" in steel_grade:
        Fy = 36.0
        E = 29000.0
    else:
        Fy = st.sidebar.number_input("Fy (ksi):", min_value=20.0, max_value=100.0, value=50.0, step=1.0)
        E = st.sidebar.number_input("E (ksi):", min_value=20000.0, max_value=35000.0, value=29000.0, step=500.0)
else:
    steel_grade = st.sidebar.selectbox("Tipo de Acero:", ["A992 / A572 Gr. 50 (Fy = 3515 kg/cm²)", "A36 (Fy = 2530 kg/cm²)", "Personalizado"])
    if "3515" in steel_grade:
        Fy = 3515.0
        E = 2040000.0
    elif "2530" in steel_grade:
        Fy = 2530.0
        E = 2040000.0
    else:
        Fy = st.sidebar.number_input("Fy (kg/cm²):", min_value=1500.0, max_value=7000.0, value=3515.0, step=50.0)
        E = st.sidebar.number_input("E (kg/cm²):", min_value=1800000.0, max_value=2200000.0, value=2040000.0, step=10000.0)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Geometría y Cargas")

if is_us:
    L_beam = st.sidebar.number_input("Claro de la Viga L (ft):", min_value=1.0, max_value=100.0, value=35.0, step=1.0)
    w_dead = st.sidebar.number_input("Carga Muerta DL (kip/ft):", min_value=0.0, max_value=50.0, value=0.4, step=0.05)
    w_live = st.sidebar.number_input("Carga Viva LL (kip/ft):", min_value=0.0, max_value=50.0, value=0.6, step=0.05)
else:
    L_beam = st.sidebar.number_input("Claro de la Viga L (m):", min_value=0.5, max_value=30.0, value=10.67, step=0.5)
    w_dead = st.sidebar.number_input("Carga Muerta DL (ton/m):", min_value=0.0, max_value=75.0, value=0.595, step=0.05)
    w_live = st.sidebar.number_input("Carga Viva LL (ton/m):", min_value=0.0, max_value=75.0, value=0.893, step=0.05)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Soporte Lateral (Lb)")
bracing_opt = st.sidebar.selectbox(
    "Condición de Arriostramiento Lateral:",
    ["Continuo (Lb = 0, Patín comprimido confinado)", "Apoyado solo en extremos (Lb = L)", "Espaciamiento uniforme (especificar Lb)"]
)

if bracing_opt.startswith("Continuo"):
    Lb_val = 0.0
elif bracing_opt.startswith("Apoyado solo"):
    Lb_val = L_beam * (12.0 if is_us else 100.0)
else:
    if is_us:
        lb_input = st.sidebar.number_input("Distancia entre apoyos Lb (ft):", min_value=0.5, max_value=float(L_beam), value=7.0, step=0.5)
        Lb_val = lb_input * 12.0
    else:
        lb_input = st.sidebar.number_input("Distancia entre apoyos Lb (m):", min_value=0.2, max_value=float(L_beam), value=2.13, step=0.1)
        Lb_val = lb_input * 100.0

cb_input = st.sidebar.number_input("Factor Cb (1.0 = conservador):", min_value=1.0, max_value=3.0, value=1.0, step=0.05)
deflect_limit_ratio = st.sidebar.selectbox("Límite de Deflexión Admisible:", ["L / 360 (Vigas de piso)", "L / 240 (Techos con cielo raso)", "L / 180 (Techos industriales)"], index=0)
deflect_div = float(deflect_limit_ratio.split("/")[1].split()[0])

# ----------------- TÍTULO PRINCIPAL -----------------
st.title("🏗️ Diseñador de Vigas de Acero a Flexión (LRFD)")
st.markdown("""
Herramienta profesional basada en la norma **AISC 360-16 / AISC 2005** y el **Manual AHMSA** (Capítulo II.2.6).
Permite revisión estado límite por estado límite, diseño automatizado y calibración contra ejercicios de clase.
""")

tabs = st.tabs(["📊 1. Revisión y Diseño de Sección", "🔍 2. Optimización y Selección Automática", "📝 3. Auditoría y Comparación de Cuaderno", "📖 4. Catálogo y Fórmulas AHMSA"])

# =========================================================================
# TAB 1: REVISIÓN Y DISEÑO
# =========================================================================
with tabs[0]:
    st.subheader("Selección del Perfil para Análisis")
    col_t1, col_t2 = st.columns([1, 2])
    
    with col_t1:
        profile_types = sorted(list(df_profiles['type'].unique()))
        sel_type = st.selectbox("Tipo de Perfil Estructural:", profile_types, index=profile_types.index('W') if 'W' in profile_types else 0)
        df_filtered = df_profiles[df_profiles['type'] == sel_type].copy()
        
        name_col = 'designation_us' if is_us else 'designation_si'
        sel_profile_name = st.selectbox("Perfil del Catálogo:", df_filtered[name_col].tolist(), index=0)
        profile_data = df_filtered[df_filtered[name_col] == sel_profile_name].iloc[0].to_dict()

    with col_t2:
        # Datos rápidos del perfil
        st.markdown(f"**Propiedades Geométricas de: `{profile_data[name_col]}`**")
        p_c1, p_c2, p_c3, p_c4 = st.columns(4)
        if is_us:
            p_c1.metric("Peralte d", f"{profile_data['d_in']:.2f} in")
            p_c1.metric("Ancho bf", f"{profile_data['bf_in']:.2f} in")
            p_c2.metric("Espesor tw", f"{profile_data['tw_in']:.3f} in")
            p_c2.metric("Espesor tf", f"{profile_data['tf_in']:.3f} in")
            p_c3.metric("Inercia Ix", f"{profile_data['Ix_in4']:.1f} in⁴")
            p_c3.metric("Módulo Zx", f"{profile_data['Zx_in3']:.1f} in³")
            p_c4.metric("Radio rts", f"{profile_data['rts_in']:.2f} in")
            p_c4.metric("Peso", f"{profile_data['weight_lbft']:.1f} lb/ft")
        else:
            p_c1.metric("Peralte d", f"{profile_data['d_mm']:.1f} mm")
            p_c1.metric("Ancho bf", f"{profile_data['bf_mm']:.1f} mm")
            p_c2.metric("Espesor tw", f"{profile_data['tw_mm']:.2f} mm")
            p_c2.metric("Espesor tf", f"{profile_data['tf_mm']:.2f} mm")
            p_c3.metric("Inercia Ix", f"{profile_data['Ix_cm4']:.0f} cm⁴")
            p_c3.metric("Módulo Zx", f"{profile_data['Zx_cm3']:.0f} cm³")
            p_c4.metric("Radio rts", f"{profile_data['rts_cm']:.2f} cm")
            p_c4.metric("Peso", f"{profile_data['weight_kgm']:.1f} kg/m")

    # Cálculos estructurales
    beam_sol = designer.calculate_simply_supported_beam(L_beam, w_dead, w_live, unit_system=unit_code)
    flex_res = designer.check_flexure_strong_axis(profile_data, Fy, E, Lb_val, Cb=cb_input, unit_system=unit_code)
    
    # Inercia para deflexión
    I_val = profile_data['Ix_in4'] if is_us else profile_data['Ix_cm4']
    delta_calc = designer.calculate_deflection(beam_sol['w_service'], L_beam, E, I_val, unit_system=unit_code)
    
    if is_us:
        delta_adm = (L_beam * 12.0) / deflect_div
        Mu_val = beam_sol['Mu']
        phi_Mn_val = flex_res['phi_Mn'] / 12.0  # kip-ft
        Vu_val = beam_sol['Vu']
        phi_Vn_val = flex_res['phi_Vn']
        unit_M = "kip-ft"
        unit_V = "kip"
        unit_D = "in"
    else:
        delta_adm = (L_beam * 100.0) / deflect_div
        Mu_val = beam_sol['Mu']
        phi_Mn_val = flex_res['phi_Mn'] * 0.00001  # kg-cm a ton-m (/1000 /100)
        Vu_val = beam_sol['Vu']
        phi_Vn_val = flex_res['phi_Vn'] * 0.001    # kg a ton
        unit_M = "ton-m"
        unit_V = "ton"
        unit_D = "cm"

    dcr_flex = Mu_val / phi_Mn_val if phi_Mn_val > 0 else 999.0
    dcr_shear = Vu_val / phi_Vn_val if phi_Vn_val > 0 else 999.0
    dcr_defl = delta_calc / delta_adm if delta_adm > 0 else 999.0

    st.markdown("---")
    st.subheader("🚦 Resultados del Diseño (Estados Límite LRFD)")

    r_c1, r_c2, r_c3 = st.columns(3)
    with r_c1:
        status_flex = "✅ CUMPLE" if dcr_flex <= 1.0 else "❌ NO CUMPLE"
        st.markdown(f"### Flexión: {status_flex}")
        st.metric("Momento Mu", f"{Mu_val:.2f} {unit_M}")
        st.metric("Resistencia ϕMn", f"{phi_Mn_val:.2f} {unit_M}")
        st.progress(min(float(dcr_flex), 1.0))
        st.caption(f"**DCR (Mu / ϕMn): {dcr_flex*100:.1f}%** | Gobierna: {flex_res['governing_state']}")

    with r_c2:
        status_shear = "✅ CUMPLE" if dcr_shear <= 1.0 else "❌ NO CUMPLE"
        st.markdown(f"### Cortante: {status_shear}")
        st.metric("Cortante Vu", f"{Vu_val:.2f} {unit_V}")
        st.metric("Resistencia ϕVn", f"{phi_Vn_val:.2f} {unit_V}")
        st.progress(min(float(dcr_shear), 1.0))
        st.caption(f"**DCR (Vu / ϕVn): {dcr_shear*100:.1f}%**")

    with r_c3:
        status_defl = "✅ CUMPLE" if dcr_defl <= 1.0 else "❌ NO CUMPLE"
        st.markdown(f"### Deflexión: {status_defl}")
        st.metric("Deflexión Δ máx", f"{delta_calc:.3f} {unit_D}")
        st.metric(f"Permisible ({deflect_limit_ratio.split()[0]})", f"{delta_adm:.3f} {unit_D}")
        st.progress(min(float(dcr_defl), 1.0))
        st.caption(f"**DCR (Δ / Δadm): {dcr_defl*100:.1f}%** (Carga de servicio DL+LL)")

    # ----------------- DESGLOSE PASO A PASO -----------------
    with st.expander("📝 Ver Memoria de Cálculo Paso a Paso (Fórmulas Detalladas)", expanded=True):
        st.markdown("#### 1. Clasificación de la Sección Transversal (Compacidad)")
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            st.markdown(f"""
            **Patín:**
            - $\\lambda_f = \\frac{{b_f}}{{2 t_f}} = {flex_res['lambda_f']:.2f}$
            - $\\lambda_{{pf}} = 0.38 \\sqrt{{\\frac{{E}}{{F_y}}}} = {flex_res['lambda_pf']:.2f}$
            - $\\lambda_{{rf}} = 1.00 \\sqrt{{\\frac{{E}}{{F_y}}}} = {flex_res['lambda_rf']:.2f}$
            - **Clasificación del patín:** `{flex_res['flange_class']}`
            """)
        with f_c2:
            st.markdown(f"""
            **Alma:**
            - $\\lambda_w = \\frac{{h}}{{t_w}} = {flex_res['lambda_w']:.2f}$
            - $\\lambda_{{pw}} = 3.76 \\sqrt{{\\frac{{E}}{{F_y}}}} = {flex_res['lambda_pw']:.2f}$
            - $\\lambda_{{rw}} = 5.70 \\sqrt{{\\frac{{E}}{{F_y}}}} = {flex_res['lambda_rw']:.2f}$
            - **Clasificación del alma:** `{flex_res['web_class']}`
            """)

        st.markdown("#### 2. Longitudes Límite para Pandeo Lateral Torsional (PLT)")
        Lp_disp = flex_res['Lp'] / (12.0 if is_us else 100.0)
        Lr_disp = flex_res['Lr'] / (12.0 if is_us else 100.0)
        Lb_disp = Lb_val / (12.0 if is_us else 100.0)
        st.markdown(f"""
        - $L_p = 1.76 r_y \\sqrt{{\\frac{{E}}{{F_y}}}} = {Lp_disp:.2f}\\text{{ {'ft' if is_us else 'm'}}}$ ({flex_res['Lp']:.2f} {'in' if is_us else 'cm'})
        - $L_r = 1.95 r_{{ts}} \\frac{{E}}{{0.7 F_y}} \\sqrt{{\\frac{{J c}}{{S_x h_o}} + \\sqrt{{\\left(\\frac{{J c}}{{S_x h_o}}\\right)^2 + 6.76 \\left(\\frac{{0.7 F_y}}{{E}}\\right)^2}}}} = {Lr_disp:.2f}\\text{{ {'ft' if is_us else 'm'}}}$ ({flex_res['Lr']:.2f} {'in' if is_us else 'cm'})
        - Longitud no arriostrada actual: $L_b = {Lb_disp:.2f}\\text{{ {'ft' if is_us else 'm'}}}$ $\\implies$ **{flex_res['ltb_zone']}**
        """)

        st.markdown("#### 3. Estados Límite de Resistencia a Flexión")
        Mp_disp = flex_res['Mp'] / (12.0 if is_us else 100000.0)
        Mn_ltb_disp = flex_res['Mn_ltb'] / (12.0 if is_us else 100000.0)
        Mn_flb_disp = flex_res['Mn_flb'] / (12.0 if is_us else 100000.0)
        Mn_disp = flex_res['Mn'] / (12.0 if is_us else 100000.0)
        st.markdown(f"""
        - **Plastificación ($M_p$):** $M_p = F_y \\cdot Z_x = {Mp_disp:.2f}\\text{{ {unit_M}}}$
        - **Pandeo Lateral Torsional ($M_{{n,LTB}}$):** ${Mn_ltb_disp:.2f}\\text{{ {unit_M}}}$
        - **Pandeo Local del Patín ($M_{{n,FLB}}$):** ${Mn_flb_disp:.2f}\\text{{ {unit_M}}}$
        - **Resistencia nominal gobernante ($M_n$):** $\\min(M_p, M_{{n,LTB}}, M_{{n,FLB}}) = {Mn_disp:.2f}\\text{{ {unit_M}}}$
        - **Resistencia de diseño LRFD ($\\phi_b M_n$ con $\\phi_b = 0.90$):** ${phi_Mn_val:.2f}\\text{{ {unit_M}}}$
        """)

    # ----------------- GRÁFICAS DE COMPORTAMIENTO -----------------
    st.markdown("---")
    st.subheader("📈 Curva de Capacidad a Flexión (Mn vs Lb)")
    
    # Generar curva Mn vs Lb para este perfil
    lb_plot_max = max(Lr_disp * 1.8, Lb_disp * 1.3, 10.0)
    lb_vals_ft = np.linspace(0.1, lb_plot_max, 120)
    mn_curve = []
    
    for lb_i in lb_vals_ft:
        lb_in = lb_i * (12.0 if is_us else 100.0)
        res_i = designer.check_flexure_strong_axis(profile_data, Fy, E, lb_in, Cb=cb_input, unit_system=unit_code)
        val = res_i['Mn'] / (12.0 if is_us else 100000.0)
        mn_curve.append(val)
        
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(lb_vals_ft, mn_curve, label=r"Resistencia Nominal $M_n$", color='#1E88E5', lw=2.5)
    ax.axhline(Mp_disp, color='#43A047', linestyle='--', label=r"$M_p$ (Plastificación)")
    ax.axvline(Lp_disp, color='#FB8C00', linestyle=':', label=f"Lp = {Lp_disp:.2f} {'ft' if is_us else 'm'}")
    ax.axvline(Lr_disp, color='#E53935', linestyle=':', label=f"Lr = {Lr_disp:.2f} {'ft' if is_us else 'm'}")
    
    # Punto de operación
    ax.scatter([Lb_disp], [Mn_disp], color='#D81B60', s=120, zorder=5, label=f"Operación: Lb = {Lb_disp:.2f}, Mn = {Mn_disp:.2f}")
    ax.axhline(Mu_val / 0.90, color='#8E24AA', linestyle='-.', alpha=0.7, label=f"Demanda requerida Mn_req = {Mu_val/0.90:.2f}")
    
    ax.set_xlabel(f"Longitud no arriostrada Lb ({'ft' if is_us else 'm'})", fontsize=11)
    ax.set_ylabel(f"Momento ({unit_M})", fontsize=11)
    ax.set_title(f"Curva de Pandeo Lateral Torsional para {profile_data[name_col]} (Cb = {cb_input})", fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=9)
    st.pyplot(fig)

# =========================================================================
# TAB 2: OPTIMIZACIÓN Y SELECCIÓN AUTOMÁTICA
# =========================================================================
with tabs[1]:
    st.subheader("🔍 Buscador de Secciones Óptimas (Menor Peso y Más Económicas)")
    st.markdown(f"""
    El motor analiza todos los perfiles de la base de datos de AHMSA para el claro de **{L_beam} {'ft' if is_us else 'm'}**,
    con carga última **$M_u = {Mu_val:.2f}\\text{{ {unit_M}}}$** y soporte lateral **$L_b = {Lb_disp:.2f}\\text{{ {'ft' if is_us else 'm'}}}$**.
    """)
    
    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        filter_type = st.multiselect("Filtrar por Familia de Perfiles:", profile_types, default=['W'])
    with c_opt2:
        max_dcr_target = st.slider("DCR Máximo permitido:", min_value=0.5, max_value=1.0, value=1.0, step=0.05)

    candidates = []
    for idx, row in df_profiles.iterrows():
        p_row = row.to_dict()
        if p_row['type'] not in filter_type:
            continue
        
        # Flexión
        f_res = designer.check_flexure_strong_axis(p_row, Fy, E, Lb_val, Cb=cb_input, unit_system=unit_code)
        p_phi_mn = (f_res['phi_Mn'] / 12.0) if is_us else (f_res['phi_Mn'] * 0.00001)
        dcr_m = Mu_val / p_phi_mn if p_phi_mn > 0 else 999.0
        
        # Cortante
        p_phi_vn = f_res['phi_Vn'] if is_us else (f_res['phi_Vn'] * 0.001)
        dcr_v = Vu_val / p_phi_vn if p_phi_vn > 0 else 999.0
        
        # Deflexión
        p_I = p_row['Ix_in4'] if is_us else p_row['Ix_cm4']
        p_delta = designer.calculate_deflection(beam_sol['w_service'], L_beam, E, p_I, unit_system=unit_code)
        dcr_d = p_delta / delta_adm if delta_adm > 0 else 999.0
        
        max_dcr = max(dcr_m, dcr_v, dcr_d)
        
        if max_dcr <= max_dcr_target:
            candidates.append({
                'Tipo': p_row['type'],
                'Designación US': p_row['designation_us'],
                'Designación SI': p_row['designation_si'],
                f"Peso ({'lb/ft' if is_us else 'kg/m'})": round(p_row['weight_lbft' if is_us else 'weight_kgm'], 1),
                f"ϕMn ({unit_M})": round(p_phi_mn, 1),
                'DCR Flexión (%)': round(dcr_m * 100, 1),
                f"Δ máx ({unit_D})": round(p_delta, 3),
                'DCR Defl (%)': round(dcr_d * 100, 1),
                'DCR Crítico (%)': round(max_dcr * 100, 1),
                'Gobierna': f_res['governing_state'].split('(')[0].strip()
            })
            
    df_cand = pd.DataFrame(candidates)
    if not df_cand.empty:
        df_cand = df_cand.sort_values(by=f"Peso ({'lb/ft' if is_us else 'kg/m'})", ascending=True).reset_index(drop=True)
        best = df_cand.iloc[0]
        st.success(f"🏆 **Perfil Óptimo Recomendado (Más Ligero):** `{best['Designación US' if is_us else 'Designación SI']}` con peso de **{best[f'Peso ({'lb/ft' if is_us else 'kg/m'})']} {'lb/ft' if is_us else 'kg/m'}** y eficiencia máxima del **{best['DCR Crítico (%)']}%**")
        st.dataframe(df_cand, use_container_width=True)
    else:
        st.warning("No se encontraron perfiles que cumplan con todos los criterios. Intenta incrementar el peralte o reducir el claro/cargas.")

# =========================================================================
# TAB 3: AUDITORÍA Y COMPARACIÓN DE CUADERNO
# =========================================================================
with tabs[2]:
    st.subheader("📝 Auditoría y Calibración con el Cuaderno de Ejercicios")
    st.markdown("""
    En esta sección comparamos los ejercicios resueltos de tu cuaderno con el cálculo riguroso del código AISC 360-16 / AHMSA.
    **Hemos verificado los números y detectado los errores de unidades y fórmulas para que puedas corregirlos.**
    """)
    
    ex_sel = st.radio("Selecciona el Ejemplo a Analizar:", ["Ejemplo 1 (Cuaderno Págs. 4-8): W18x86, L = 35 ft", "Ejemplo 2 (Cuaderno Págs. 9-11): W12x53, L = 40 ft"])
    
    if "Ejemplo 1" in ex_sel:
        st.markdown("### 📋 Ejemplo 1: Viga W18x86 ($L = 35\\text{ ft}, DL = 0.4\\text{ k/ft}, LL = 0.6\\text{ k/ft}$)")
        
        # Comparación tabular
        col_comp1, col_comp2 = st.columns([1, 1])
        with col_comp1:
            st.info("📌 **Valores del Cuaderno de Notas:**\n"
                    "- $w_u = 1.2(0.4) + 1.6(0.6) = 1.44\\text{ kip/ft}$\n"
                    "- $M_u = \\frac{1.44(35)^2}{8} = 220.5\\text{ kip-ft} = 2646\\text{ kip-in}$\n"
                    "- $\\Delta_{adm} = 35/360 = 0.097\\text{ ft} = 1.17\\text{ in}$\n"
                    "- Despeje de $I$: sustituyó $M_u = 2646$ en lugar de $w$ y usó $w_u$ en vez de $w_{serv}$\n"
                    "- Deflexión posterior: calculó $\\Delta = 1.09\\text{ in}$ dividiendo entre $I_x = 63,700$ sin convertir $\\text{cm}^4$ a $\\text{in}^4$\n"
                    "- $L_p = 111.05\\text{ in} = 9.25\\text{ ft}$ (usando $0.7 F_y$ dentro de la raíz)\n"
                    "- $L_r = 340.39\\text{ in} = 28.36\\text{ ft}$\n"
                    "- $F_{cr} = 16.38\\text{ ksi}$ (con $L_b = 35\\text{ ft}$ sin arriostrar)\n"
                    "- $\\phi M_n = 203.99\\text{ kip-ft} < M_u = 220.5\\text{ kip-ft} \\implies$ No pasa sin arriostrar $\\implies$ Propone apoyos cada $7\\text{ ft}$.")

        with col_comp2:
            st.success("🔬 **Cálculo Riguroso Corregido (AISC 360-16 / AHMSA):**\n"
                       "- $w_u = 1.44\\text{ kip/ft}$ $\\rightarrow$ **¡Correcto en el cuaderno!**\n"
                       "- $M_u = 220.50\\text{ kip-ft} = 2646.0\\text{ kip-in}$ $\\rightarrow$ **¡Correcto!**\n"
                       "- Deflexión real de servicio ($w_{serv} = 0.4 + 0.6 = 1.0\\text{ kip/ft}$, $I_x = 1530.4\\text{ in}^4$):\n"
                       "  $$\\Delta = \\frac{5 (1.0/12) (420)^4}{384 (29000) (1530.4)} = \\mathbf{0.76\\text{ in}} < 1.17\\text{ in}$$ $\\rightarrow$ **Pasa con holgura (65% DCR).**\n"
                       "- $L_p$ correcto: $1.76 r_y \\sqrt{\\frac{E}{F_y}} = 1.76 (2.63) \\sqrt{\\frac{29000}{50}} = \\mathbf{111.47\\text{ in} = 9.29\\text{ ft}}$\n"
                       "- $L_r$ correcto: $\\mathbf{340.94\\text{ in} = 28.41\\text{ ft}}$\n"
                       "- $F_{cr}$ exacto para $L_b = 35\\text{ ft}$ con $C_b = 1.0$: $\\mathbf{26.28\\text{ ksi}}$\n"
                       "- Con apoyos cada $L_b = 7\\text{ ft} = 84\\text{ in} < L_p = 111.5\\text{ in}$ (Zona 1: Plastificación):\n"
                       "  $$M_n = M_p = F_y Z_x = (50)(186.1) = 9305\\text{ kip-in} = 775.4\\text{ kip-ft}$$\n"
                       "  $$\\phi M_n = 0.90(775.4) = \\mathbf{697.9\\text{ kip-ft}} \\gg 220.5\\text{ kip-ft}$$ $\\rightarrow$ **Cumple con DCR = 31.6%**")

        st.warning("""
        ⚠️ **Resumen de Errores a Corregir en tus Notas (Ejemplo 1):**
        1. **Fórmula de $L_p$ (pág. 5):** Escribiste $L_p = 1.76 r_y \\sqrt{\\frac{E}{0.7 F_y}}$. ¡El factor $0.7$ no va en $L_p$, solo se usa en $L_r$! La fórmula correcta es $L_p = 1.76 r_y \\sqrt{\\frac{E}{F_y}}$.
        2. **Despeje de Inercia (pág. 4):** Pusiste el momento $2646$ en lugar de la carga $w$, y además usaste la carga factorizada $1.44$ en vez de la de servicio $1.0\\text{ kip/ft}$.
        3. **Unidades de Inercia en Deflexión (pág. 5):** Tomaste $I_x = 63,700\\text{ cm}^4$ del catálogo y lo pusiste tal cual en una fórmula que tenía $E = 29,000\\text{ ksi}$ y longitud en pulgadas ($1530.4\\text{ in}^4$).
        """)

    else:
        st.markdown("### 📋 Ejemplo 2: Viga W12x53 ($L = 40\\text{ ft}, DL = 0.05\\text{ k/ft}, LL = 0.07\\text{ k/ft}$)")
        col_e2_1, col_e2_2 = st.columns([1, 1])
        with col_e2_1:
            st.info("📌 **Valores del Cuaderno de Notas:**\n"
                    "- $w_u = 1.2(0.05) + 1.6(0.07) = 0.172\\text{ kip/ft}$\n"
                    "- $M_u = \\frac{0.172(40)^2}{8} = 34.40\\text{ kip-ft} = 412.80\\text{ kip-in}$\n"
                    "- En la pág. 9 anotó: `$S_y = 315\\text{ in}^3$` y `$Z_y = 477\\text{ in}^3$`\n"
                    "- Calculó: $M_n = (50\\text{ ksi})(477\\text{ in}^3) = \\mathbf{23,850\\text{ kip-in}} = 1,987.5\\text{ kip-ft}$\n"
                    "- En la pág. 11 calculó $F_{cr} = 10.145\\text{ ksi}$ usando fórmulas de eje menor mezcladas.")

        with col_e2_2:
            st.success("🔬 **Cálculo Riguroso Corregido (AISC 360-16 / AHMSA):**\n"
                       "- $w_u = 0.172\\text{ kip/ft}$ $\\rightarrow$ **¡Correcto!**\n"
                       "- $M_u = 34.40\\text{ kip-ft} = 412.80\\text{ kip-in}$ $\\rightarrow$ **¡Correcto!**\n"
                       "- **¡Corrección Crítica de Unidades de Catálogo!**\n"
                       "  En el catálogo AHMSA (pág. 273): $S_y = 315\\mathbf{\\text{ cm}^3}$ y $Z_y = 477\\mathbf{\\text{ cm}^3}$.\n"
                       "  Convertidos a pulgadas cúbicas:\n"
                       "  $$S_y = \\frac{315}{2.54^3} = \\mathbf{19.22\\text{ in}^3} \\quad (\\text{no } 315\\text{ in}^3!)$$\n"
                       "  $$Z_y = \\frac{477}{2.54^3} = \\mathbf{29.11\\text{ in}^3} \\quad (\\text{no } 477\\text{ in}^3!)$$\n"
                       "- Capacidad real en el eje débil (eje Y):\n"
                       "  $$M_n = F_y \\cdot Z_y = (50)(29.11) = \\mathbf{1455.5\\text{ kip-in} = 121.3\\text{ kip-ft}}$$\n"
                       "  $$\\phi M_n = 0.90 (121.3) = \\mathbf{109.16\\text{ kip-ft}}$$\n"
                       "- Capacidad real en el eje fuerte (eje X, $Z_x = 78.1\\text{ in}^3$):\n"
                       "  $$M_p = (50)(78.1) = 3905.5\\text{ kip-in} = 325.5\\text{ kip-ft}$$\n"
                       "  $$\\phi M_p = \\mathbf{292.9\\text{ kip-ft}}$$"
                       )

        st.error("""
        🚨 **Error Crítico en el Cuaderno (Ejemplo 2):**
        Copiaste las cifras de $S_y = 315$ y $Z_y = 477$ de la columna del manual AHMSA que está en **$\\text{cm}^3$**, pero las etiquetaste como **$\\text{in}^3$**.
        Como $1\\text{ in}^3 = 16.387\\text{ cm}^3$, **¡la resistencia plástica en tu cuaderno resultó 16.4 veces mayor de lo real!**
        Un perfil W12x53 jamás podría resistir $23,850\\text{ kip-in}$ ($1,987\\text{ kip-ft}$), su resistencia real a flexión en eje débil es de $1,455\\text{ kip-in}$ ($121.3\\text{ kip-ft}$).
        """)

# =========================================================================
# TAB 4: CATÁLOGO Y FÓRMULAS
# =========================================================================
with tabs[3]:
    st.subheader("📖 Catálogo AHMSA y Manual de Fórmulas de Referencia")
    
    st.markdown("### Tabla Interactiva de Perfiles")
    cat_type = st.selectbox("Familia de perfil a visualizar:", df_profiles['type'].unique())
    df_cat_show = df_profiles[df_profiles['type'] == cat_type]
    
    if is_us:
        cols_show = ['designation_us', 'weight_lbft', 'd_in', 'bf_in', 'tw_in', 'tf_in', 'Ix_in4', 'Sx_in3', 'Zx_in3', 'ry_in', 'rts_in', 'ho_in', 'J_in4']
    else:
        cols_show = ['designation_si', 'weight_kgm', 'd_mm', 'bf_mm', 'tw_mm', 'tf_mm', 'Ix_cm4', 'Sx_cm3', 'Zx_cm3', 'ry_cm', 'rts_cm', 'ho_cm', 'J_cm4']
        
    st.dataframe(df_cat_show[cols_show], use_container_width=True)
    
    st.markdown("""
    ---
    ### Resumen de Ecuaciones de Diseño AISC 360-16 / AHMSA II.2.6

    1. **Factor de Resistencia a Flexión:** $\\phi_b = 0.90$ (LRFD).
    2. **Zona 1 (Plastificación, $L_b \\le L_p$):**
       $$M_n = M_p = F_y Z_x$$
       $$L_p = 1.76 r_y \\sqrt{\\frac{E}{F_y}}$$
    3. **Zona 2 (Pandeo Lateral Torsional Inelástico, $L_p < L_b \\le L_r$):**
       $$M_n = C_b \\left[ M_p - (M_p - 0.7 F_y S_x) \\left(\\frac{L_b - L_p}{L_r - L_p}\\right) \\right] \\le M_p$$
       $$L_r = 1.95 r_{ts} \\frac{E}{0.7 F_y} \\sqrt{\\frac{J c}{S_x h_o} + \\sqrt{\\left(\\frac{J c}{S_x h_o}\\right)^2 + 6.76 \\left(\\frac{0.7 F_y}{E}\\right)^2}}$$
    4. **Zona 3 (Pandeo Lateral Torsional Elástico, $L_b > L_r$):**
       $$M_n = F_{cr} S_x \\le M_p$$
       $$F_{cr} = \\frac{C_b \\pi^2 E}{\\left(\\frac{L_b}{r_{ts}}\\right)^2} \\sqrt{1 + 0.078 \\frac{J c}{S_x h_o} \\left(\\frac{L_b}{r_{ts}}\\right)^2}$$
    5. **Pandeo Local del Patín (FLB):**
       $$\\lambda_f = \\frac{b_f}{2 t_f}, \\quad \\lambda_{pf} = 0.38 \\sqrt{\\frac{E}{F_y}}, \\quad \\lambda_{rf} = 1.00 \\sqrt{\\frac{E}{F_y}}$$
    """)

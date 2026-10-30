"""
Módulo de cálculo y diseño estructural para elementos de acero sometidos a flexión.
Basado en especificaciones AISC 360-16 / AISC 2005 y Manual de Diseño AHMSA (Cap. II.2.6).
Método: LRFD (Load and Resistance Factor Design).
Soporta Sistema Métrico e Inglés.
"""

import math
from typing import Dict, Any, Tuple

class SteelBeamDesigner:
    def __init__(self):
        # Constantes y factores
        self.phi_b = 0.90  # Factor de resistencia por flexión LRFD
        self.phi_v_compact = 1.00  # Factor para cortante en perfiles laminados que cumplen G2.1a
        self.phi_v_general = 0.90

    @staticmethod
    def calculate_cb(Mmax: float, MA: float, MB: float, MC: float, Rm: float = 1.0) -> float:
        """
        Calcula el factor de modificación por momento no uniforme Cb (AISC F1-1).
        Cb = 12.5*Mmax / (2.5*Mmax + 3*MA + 4*MB + 3*MC) * Rm <= 3.0
        """
        Mmax = abs(Mmax)
        MA = abs(MA)
        MB = abs(MB)
        MC = abs(MC)
        if Mmax <= 1e-9:
            return 1.0
        denom = 2.5 * Mmax + 3.0 * MA + 4.0 * MB + 3.0 * MC
        if denom <= 1e-9:
            return 1.0
        cb = (12.5 * Mmax / denom) * Rm
        return min(cb, 3.0)

    def check_flexure_strong_axis(self, profile: Dict[str, Any], Fy: float, E: float,
                                  Lb: float, Cb: float = 1.0, unit_system: str = 'US') -> Dict[str, Any]:
        """
        Revisión de viga a flexión alrededor del eje fuerte (eje X) según AISC 360 / AHMSA.
        
        Parámetros:
        - profile: diccionario con propiedades del perfil
        - Fy: esfuerzo de fluencia (ksi en US, kg/cm2 o MPa en SI)
        - E: módulo de elasticidad (ksi en US, kg/cm2 o MPa en SI)
        - Lb: longitud no arriostrada lateralmente (in en US, cm en SI)
        - Cb: factor de momento no uniforme
        - unit_system: 'US' (kip, in, ft) o 'SI' (ton, kg, cm, m)
        """
        # Extraer propiedades según el sistema de unidades
        if unit_system == 'US':
            d = profile['d_in']
            bf = profile['bf_in']
            tw = profile['tw_in']
            tf = profile['tf_in']
            h = profile['h_in']
            Sx = profile['Sx_in3']
            Zx = profile['Zx_in3']
            ry = profile['ry_in']
            rts = profile['rts_in']
            ho = profile['ho_in']
            J = profile['J_in4']
            Cw = profile['Cw_in6']
            Iy = profile['Iy_in4']
            Ix = profile['Ix_in4']
        else:
            d = profile['d_mm'] * 0.1  # cm
            bf = profile['bf_mm'] * 0.1
            tw = profile['tw_mm'] * 0.1
            tf = profile['tf_mm'] * 0.1
            h = profile['h_mm'] * 0.1
            Sx = profile['Sx_cm3']
            Zx = profile['Zx_cm3']
            ry = profile['ry_cm']
            rts = profile['rts_cm']
            ho = profile['ho_cm']
            J = profile['J_cm4']
            Cw = profile['Cw_cm6']
            Iy = profile['Iy_cm4']
            Ix = profile['Ix_cm4']

        ptype = profile.get('type', 'W')

        # 1. PARÁMETROS DE ESBELTEZ LOCAL (COMPACIDAD)
        # Patín
        lambda_f = bf / (2.0 * tf)
        lambda_pf = 0.38 * math.sqrt(E / Fy)
        lambda_rf = 1.0 * math.sqrt(E / Fy)

        if lambda_f <= lambda_pf:
            flange_class = 'Compacto'
        elif lambda_f <= lambda_rf:
            flange_class = 'No Compacto'
        else:
            flange_class = 'Esbelto'

        # Alma
        lambda_w = h / tw
        lambda_pw = 3.76 * math.sqrt(E / Fy)
        lambda_rw = 5.70 * math.sqrt(E / Fy)

        if lambda_w <= lambda_pw:
            web_class = 'Compacta'
        elif lambda_w <= lambda_rw:
            web_class = 'No Compacta'
        else:
            web_class = 'Esbelta'

        is_compact_section = (flange_class == 'Compacto') and (web_class == 'Compacta')

        # 2. MOMENTO PLÁSTICO (FLUENCIA / PLASTIFICACIÓN)
        Mp = Fy * Zx

        # 3. PANDEO LATERAL TORSIONAL (PLT)
        # Factor c: 1.0 para I/W, para canales c = (ho/2)*sqrt(Iy/Cw)
        if ptype == 'C' and Cw > 0:
            c = (ho / 2.0) * math.sqrt(Iy / Cw)
        else:
            c = 1.0

        # Longitudes límite Lp y Lr
        Lp = 1.76 * ry * math.sqrt(E / Fy)

        # Lr (F2-6)
        rts_val = rts if rts > 0 else ry
        term1 = 1.95 * rts_val * (E / (0.7 * Fy))
        jc_over_sxho = (J * c) / (Sx * ho) if (Sx * ho) > 0 else 0
        radicand = jc_over_sxho + math.sqrt(jc_over_sxho**2 + 6.76 * ((0.7 * Fy) / E)**2)
        Lr = term1 * math.sqrt(radicand)

        # Evaluación según Lb
        if Lb <= Lp:
            ltb_zone = 'Zona 1 (Lb <= Lp): Plastificación'
            Mn_ltb = Mp
            Fcr = None
        elif Lb <= Lr:
            ltb_zone = 'Zona 2 (Lp < Lb <= Lr): PLT Inelástico'
            Mn_ltb = Cb * (Mp - (Mp - 0.7 * Fy * Sx) * ((Lb - Lp) / (Lr - Lp)))
            Mn_ltb = min(Mn_ltb, Mp)
            Fcr = None
        else:
            ltb_zone = 'Zona 3 (Lb > Lr): PLT Elástico'
            slender = Lb / rts_val
            Fcr_term = (Cb * (math.pi**2) * E) / (slender**2)
            Fcr_mult = math.sqrt(1.0 + 0.078 * ((J * c) / (Sx * ho)) * (slender**2))
            Fcr = Fcr_term * Fcr_mult
            Mn_ltb = min(Fcr * Sx, Mp)

        # 4. PANDEO LOCAL DEL PATÍN (FLB)
        if flange_class == 'Compacto':
            Mn_flb = Mp
        elif flange_class == 'No Compacto':
            Mn_flb = Mp - (Mp - 0.7 * Fy * Sx) * ((lambda_f - lambda_pf) / (lambda_rf - lambda_pf))
        else:
            # Esbelto (F3-2)
            kc = 4.0 / math.sqrt(lambda_w) if lambda_w > 0 else 0.76
            kc = max(0.35, min(0.76, kc))
            Mn_flb = (0.9 * E * kc * Sx) / (lambda_f**2)

        # 5. RESISTENCIA NOMINAL Y DE DISEÑO
        governing_state = 'Plastificación total (Mp)'
        Mn = Mp

        if Mn_ltb < Mn:
            Mn = Mn_ltb
            governing_state = f"Pandeo Lateral Torsional ({ltb_zone})"

        if Mn_flb < Mn:
            Mn = Mn_flb
            governing_state = f"Pandeo Local del Patín ({flange_class})"

        phi_Mn = self.phi_b * Mn

        # Cortante nominal (G2)
        Aw = d * tw
        limit_shear = 2.24 * math.sqrt(E / Fy)
        if lambda_w <= limit_shear and ptype in ['W', 'IR']:
            phi_v = self.phi_v_compact
            Cv = 1.0
        else:
            phi_v = self.phi_v_general
            if lambda_w <= 1.10 * math.sqrt(5.0 * E / Fy):
                Cv = 1.0
            else:
                Cv = (1.10 * math.sqrt(5.0 * E / Fy)) / lambda_w

        Vn = 0.6 * Fy * Aw * Cv
        phi_Vn = phi_v * Vn

        return {
            'unit_system': unit_system,
            'lambda_f': lambda_f,
            'lambda_pf': lambda_pf,
            'lambda_rf': lambda_rf,
            'flange_class': flange_class,
            'lambda_w': lambda_w,
            'lambda_pw': lambda_pw,
            'lambda_rw': lambda_rw,
            'web_class': web_class,
            'is_compact_section': is_compact_section,
            'Mp': Mp,
            'Lp': Lp,
            'Lr': Lr,
            'Lb': Lb,
            'ltb_zone': ltb_zone,
            'Fcr': Fcr,
            'Mn_ltb': Mn_ltb,
            'Mn_flb': Mn_flb,
            'Mn': Mn,
            'phi_Mn': phi_Mn,
            'governing_state': governing_state,
            'Vn': Vn,
            'phi_Vn': phi_Vn,
            'Aw': Aw,
            'Ix': Ix,
            'Sx': Sx,
            'Zx': Zx
        }

    def check_flexure_weak_axis(self, profile: Dict[str, Any], Fy: float, E: float,
                                unit_system: str = 'US') -> Dict[str, Any]:
        """
        Revisión a flexión en el eje menor (eje Y) según AISC 360 Sección F6.
        """
        if unit_system == 'US':
            bf = profile['bf_in']
            tf = profile['tf_in']
            Sy = profile['Sy_in3']
            Zy = profile['Zy_in3']
        else:
            bf = profile['bf_mm'] * 0.1
            tf = profile['tf_mm'] * 0.1
            Sy = profile['Sy_cm3']
            Zy = profile['Zy_cm3']

        lambda_f = bf / (2.0 * tf)
        lambda_pf = 0.38 * math.sqrt(E / Fy)
        lambda_rf = 1.0 * math.sqrt(E / Fy)

        # F6-1: Mp = Fy * Zy <= 1.6 * Fy * Sy
        Mp = min(Fy * Zy, 1.6 * Fy * Sy)

        if lambda_f <= lambda_pf:
            flange_class = 'Compacto'
            Mn = Mp
        elif lambda_f <= lambda_rf:
            flange_class = 'No Compacto'
            Mn = Mp - (Mp - 0.7 * Fy * Sy) * ((lambda_f - lambda_pf) / (lambda_rf - lambda_pf))
        else:
            flange_class = 'Esbelto'
            Fcr = (0.69 * E) / (lambda_f**2)
            Mn = Fcr * Sy

        phi_Mn = self.phi_b * Mn

        return {
            'unit_system': unit_system,
            'axis': 'Y (menor / débil)',
            'lambda_f': lambda_f,
            'lambda_pf': lambda_pf,
            'lambda_rf': lambda_rf,
            'flange_class': flange_class,
            'Mp': Mp,
            'Mn': Mn,
            'phi_Mn': phi_Mn,
            'Sy': Sy,
            'Zy': Zy
        }

    @staticmethod
    def calculate_simply_supported_beam(L_length: float, w_dead: float, w_live: float,
                                        unit_system: str = 'US') -> Dict[str, Any]:
        """
        Calcula solicitaciones para viga simplemente apoyada con carga uniforme.
        
        En US:
        - L_length en ft
        - w_dead, w_live en kip/ft
        
        En SI:
        - L_length en m
        - w_dead, w_live en ton/m
        """
        w_service = w_dead + w_live
        # Combinaciones LRFD
        u1 = 1.4 * w_dead
        u2 = 1.2 * w_dead + 1.6 * w_live
        wu = max(u1, u2)

        Mu = (wu * (L_length**2)) / 8.0  # kip-ft o ton-m
        Vu = (wu * L_length) / 2.0      # kip o ton

        return {
            'w_dead': w_dead,
            'w_live': w_live,
            'w_service': w_service,
            'wu_comb1_4D': u1,
            'wu_comb1_2D_1_6L': u2,
            'wu_gov': wu,
            'Mu': Mu,
            'Vu': Vu,
            'L': L_length
        }

    @staticmethod
    def calculate_deflection(w_service: float, L_length: float, E: float, I: float,
                             unit_system: str = 'US') -> float:
        """
        Calcula la deflexión máxima Delta = 5*w*L^4 / (384*E*I).
        
        En US:
        - w_service en kip/ft -> se convierte a kip/in (/12)
        - L_length en ft -> se convierte a in (*12)
        - E en ksi
        - I en in4
        - Retorna Delta en pulgadas (in)
        
        En SI:
        - w_service en ton/m -> se convierte a kg/cm (/10)
        - L_length en m -> se convierte a cm (*100)
        - E en kg/cm2
        - I en cm4
        - Retorna Delta en cm
        """
        if unit_system == 'US':
            w_in = w_service / 12.0
            L_in = L_length * 12.0
            delta = (5.0 * w_in * (L_in**4)) / (384.0 * E * I)
            return delta
        else:
            w_cm = (w_service * 1000.0) / 100.0  # kg/cm
            L_cm = L_length * 100.0              # cm
            delta = (5.0 * w_cm * (L_cm**4)) / (384.0 * E * I)
            return delta

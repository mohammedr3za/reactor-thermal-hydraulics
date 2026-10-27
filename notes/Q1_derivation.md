# Q1: maximum permissible linear heat rate (analytical)

## Scope

Find the linear heat rate $q'$ at which the pellet centre reaches 2000 °C and the linear heat
rate at which the clad reaches 1200 °C. The smaller value is the permissible limit.

| Item | Value |
|---|---|
| Lattice | triangular, pitch $p$ = 12.5 mm |
| Clad outer diameter | $d_{co}$ = 10 mm; clad thickness 0.5 mm; $d_{ci}$ = 9 mm |
| Pellet diameter | $d_p$ = 9 mm (= $d_{ci}$: **no gap**) |
| Rod | 4 m overall, 3 m active |
| Coolant | water, $T_b$ = 310 °C, 180 bar, $V$ = 5 m/s |
| Limits | $T_c$ < 2000 °C, $T_{clad}$ < 1200 °C |

Assumptions: steady state, uniform heat generation, no axial conduction, ideal pellet–clad
contact (gap conductance is a sensitivity), UO$_2$ at 95 % theoretical density, Zircaloy-4 clad,
single-phase coolant.

## Model

Resistances per metre of rod, in series:

$$R_{film} = \frac{1}{h\,\pi d_{co}}, \qquad R_{clad} = \frac{\ln(d_{co}/d_{ci})}{2\pi k_c}, \qquad R_{gap} = \frac{1}{h_{gap}\,\pi d_{ci}}$$

Pellet with uniform heat generation $q'''$ and $q' = \pi r_p^2 q'''$:

$$\frac{1}{r}\frac{d}{dr}\left(k_f\,r\,\frac{dT}{dr}\right) + q''' = 0 \quad\Rightarrow\quad \int_{T_s}^{T_c} k_f\,dT = \frac{q'}{4\pi}$$

With the mean conductivity $\bar k_f$ over the pellet range, $R_{fuel} = 1/(4\pi\bar k_f)$. The two limits:

$$q'_{fuel} = \frac{T_{c,max} - T_b}{R_{film} + R_{clad} + R_{gap} + R_{fuel}}, \qquad q'_{clad} = \frac{T_{ci,max} - T_b}{R_{film} + R_{clad}}$$

The hottest clad point is the inner surface. The fuel limit is a fixed point on $q'$, because
$T_s = T_b + q'(R_{film} + R_{clad} + R_{gap})$ depends on $q'$.

## Film coefficient

Interior sub-channel of the triangular lattice:

$$D_e = d_{co}\left[\frac{2\sqrt3}{\pi}\left(\frac{p}{d_{co}}\right)^2 - 1\right] = 7.23\ \mathrm{mm}$$

Weisman (1959), Todreas–Kazimi form, triangular array, $1.1 \le p/d \le 1.5$:

$$\mathrm{Nu} = 0.023\,\mathrm{Re}^{0.8}\,\mathrm{Pr}^{0.4}\left[1.130\,\frac{p}{d_{co}} - 0.2609\right], \qquad h = \frac{\mathrm{Nu}\,k}{D_e}$$

Water properties from IAPWS-IF97 at 310 °C, 180 bar.

## Material properties

Zircaloy (MATPRO), $T$ in K, at the mean clad temperature:

$$k_c = 7.51 + 2.09\times10^{-2}T - 1.45\times10^{-5}T^2 + 7.67\times10^{-9}T^3$$

UO$_2$, 95 % TD (Fink, J. Nucl. Mater. 279 (2000) 1), $t = T/1000$ K:

$$k_f = \frac{100}{7.5408 + 17.692\,t + 3.6142\,t^2} + \frac{6400}{t^{5/2}}e^{-16.35/t}$$

Its integral from 0 °C to the melting point (2840 °C) is 89.5 W/cm; the classic value is 93 W/cm.

## Procedure

1. $h$ from the Weisman correlation; $R_{film}$. $k_c$ at the mean clad temperature; $R_{clad}$.
2. Clad limit: $q'_{clad} = (1200 - 310)/(R_{film} + R_{clad})$.
3. Fuel limit: guess $q'$, compute $T_s$, set $q' = 4\pi\int_{T_s}^{2000\,°\mathrm{C}} k_f\,dT$, repeat to convergence.
4. Report the smaller $q'$ and the interface temperatures.

## Results (from `code/fuel_rod.py`)

| Quantity | Value |
|---|---|
| $h$ | 46 100 W/m² K (Re = 3.0 × 10⁵, Nu = 604) |
| $R_{film}$, $R_{clad}$, $R_{fuel}$ | 6.90 × 10⁻⁴, 9.83 × 10⁻⁴, 2.89 × 10⁻² K m/W |
| $q'_{fuel}$ | **55.4 kW/m** (binding) |
| $q'_{clad}$ | 668 kW/m |
| Temperatures at $q'_{max}$ | $T_{co}$ = 348 °C, $T_{ci}$ = $T_s$ = 403 °C, $T_c$ = 2000 °C |

Sensitivity: Dittus–Boelter film 55.1; gap 10 000 W/m²K 47.0; gap 5000 W/m²K 41.3; coolant
290 °C 56.4; coolant 330 °C 54.3 kW/m. The clad outer surface stays 9 K below saturation.

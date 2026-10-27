# Q2: once-through steam generator, assumptions and calculation scheme

## Duty and flows

$$Q_{SG} = \frac{P_e}{\eta N_{loops}} = \frac{1000\ \mathrm{MW}}{0.32 \times 4} = 781.25\ \mathrm{MW}, \qquad \dot m_p = \frac{Q_{SG}}{h_{p,in} - h_{p,out}}, \qquad \dot m_s = \frac{Q_{SG}}{h_{s,out} - h_{fw}}$$

Primary (tube side): 180 bar (the core pressure of Q1), 325 °C in at the top, 295 °C out at the
bottom. Secondary (shell side): feedwater at $T_{sat}(P_{in}) - 20$ K enters at the bottom; steam
leaves the top at the outlet pressure and 320 °C. Pump heat and losses are neglected.

## Feasibility of the specification

At 100 bar, $T_{sat}$ = 311.0 °C. The primary leaves at 295 °C. With $Q$ the heat transferred
from the cold end,

$$h_p(Q) = h_{p,out} + \frac{Q}{\dot m_p}, \qquad h_s(Q) = h_{fw} + \frac{Q}{\dot m_s}, \qquad \Delta T(Q) = T_p(Q) - T_s(Q)$$

The minimum of $\Delta T$ is −13.5 K at 8 % of the duty. The temperature profiles cross. No
exchanger of any type can meet the specification. This is a thermodynamic limit.

Correction adopted: keep all primary-side values, the 320 °C outlet and the 20 K subcooling;
lower the steam pressure to **70 bar**. This is the largest round pressure with an approach of
10 K or more at the onset of boiling (exact limit 71.1 bar). Result: $T_{sat}$ = 285.8 °C,
superheat 34 K, approach 11.1 K at the onset of boiling, 5 K at the hot end. Alternatives
(higher primary temperatures) put the core outlet within 12 K of saturation at 180 bar.

## Configuration

Vertical once-through unit (Babcock & Wilcox type). Straight tubes. Primary flows **down** inside
the tubes. Secondary flows **up** in the shell, parallel to the tubes, through broached support
plates; no segmental baffles. Shell-side regions from the bottom: subcooled liquid, nucleate
boiling, post-dryout flow, superheated steam.

## Design choices (parameters of `DESIGN` in `code/sg_design.py`)

| Item | Value | Basis |
|---|---|---|
| Tube OD | 15.875 mm (5/8 in) | OTSG practice |
| Tube wall | $t = P d_o/(2SE + 0.8P)$, rounded up to BWG 17 = 1.473 mm | design pressure 1.1 × 180 bar, shell depressurised |
| Material | SS316: $S$ = 115 MPa (ASME II-D Table 1A, 16.6 ksi at 650 °F), $E$ = 1, $k$ = 17.5 W/m K, $\rho$ = 8000 kg/m³ | |
| Pitch | triangular, $p/d_o$ = 1.3 | ligament above the TEMA minimum; 1.4 lengthens the bundle by 10 % |
| Tube-side velocity | 3.5 m/s | velocity sweep: 5 m/s gives 26 m tubes, 3.5 m/s gives 19 m |
| Fouling | 2.5 × 10⁻⁵ m² K/W each side | clean primary water, treated feedwater |
| Dryout | $x_{do}$ = 0.90 | look-up table at 7 MPa, $G$ ≈ 200 kg/m² s, $q''$ ≈ 0.1 MW/m² |
| Support plates | every 1.0 m, $K$ = 0.5 | assumed |
| Shell | $D_s = D_{otl}$ + 50 mm; 0.93 bundle area utilisation; $t = PR/(SE - 0.6P)$ at 1.1 × $P_{in}$ | ASME VIII UG-27 |
| Heads, tubesheets | $t_{head} = PR/(2SE - 0.2P)$; $T_{ts} = (D/3)\sqrt{P/S}$ | primary design pressure |
| Tube ends | $K$ = 1.5 | entrance and exit |

## Correlations

Single phase (Dittus–Boelter), $n$ = 0.3 for the cooled tube side, 0.4 for the heated shell side,
on $D_e = d_o[(2\sqrt3/\pi)(p/d_o)^2 - 1]$ for the shell:

$$\mathrm{Nu} = 0.023\,\mathrm{Re}^{0.8}\,\mathrm{Pr}^{n}$$

Chen (1966) for subcooled and saturated boiling:

$$h_{TP} = F h_l + S h_{FZ}, \qquad h_l = 0.023\,\mathrm{Re}_l^{0.8}\mathrm{Pr}_l^{0.4}\frac{k_l}{D_e}, \qquad \mathrm{Re}_l = \frac{G(1-x)D_e}{\mu_l}$$

$$\frac{1}{X_{tt}} = \left(\frac{x}{1-x}\right)^{0.9}\left(\frac{\rho_l}{\rho_g}\right)^{0.5}\left(\frac{\mu_g}{\mu_l}\right)^{0.1}, \qquad F = \begin{cases}1 & 1/X_{tt} \le 0.1\\ 2.35(1/X_{tt} + 0.213)^{0.736} & 1/X_{tt} > 0.1\end{cases}$$

$$S = \frac{1}{1 + 2.53\times10^{-6}(\mathrm{Re}_l F^{1.25})^{1.17}}, \qquad h_{FZ} = 0.00122\,\frac{k_l^{0.79}c_{p,l}^{0.45}\rho_l^{0.49}}{\sigma^{0.5}\mu_l^{0.29}h_{fg}^{0.24}\rho_g^{0.24}}\,\Delta T_{sat}^{0.24}\Delta p_{sat}^{0.75}$$

In the subcooled region $x$ = 0, $F$ = 1; the convective term acts on $(T_w - T_b)$, the nucleate
term on $(T_w - T_{sat})$ when $T_w > T_{sat}$.

Dougall–Rohsenow for post-dryout flow, thermal equilibrium:

$$h = 0.023\,\frac{k_g}{D_e}\left[\frac{G D_e}{\mu_g}\left(x + \frac{\rho_g}{\rho_l}(1-x)\right)\right]^{0.8}\mathrm{Pr}_g^{0.4}$$

Friction (Filonenko, Darcy, smooth) and homogeneous two-phase properties:

$$f = (0.79\ln\mathrm{Re} - 1.64)^{-2}, \qquad \frac{1}{\rho_H} = \frac{x}{\rho_g} + \frac{1-x}{\rho_l}, \qquad \frac{1}{\mu_H} = \frac{x}{\mu_g} + \frac{1-x}{\mu_l}$$

Shell-side pressure drop per segment:

$$\Delta p = f\frac{\Delta z}{D_e}\frac{G_s^2}{2\rho_H} + \rho_H g\Delta z + G_s^2\Delta\!\left(\frac{1}{\rho_H}\right) + K\frac{G_s^2}{2\rho_H}$$

Local heat flux, all resistances on the outer surface, $T_w$ by bisection:

$$q'' = \frac{T_p - T_w}{R_{in}} = q''_{shell}(T_w), \qquad R_{in} = \frac{d_o}{d_i}\left(\frac{1}{h_i} + R_{f,i}\right) + \frac{d_o\ln(d_o/d_i)}{2k_w} + R_{f,o}$$

## Marching scheme

Both streams are known at the bottom (primary outlet, feedwater inlet). The march starts there;
no shooting is needed. For segment $i$ of height $\Delta z$:

$$\Delta Q_i = q''_i N\pi d_o\Delta z, \qquad h_{s,i+1} = h_{s,i} + \frac{\Delta Q_i}{\dot m_s}, \qquad h_{p,i+1} = h_{p,i} + \frac{\Delta Q_i}{\dot m_p}$$

1. Local secondary state $(P, h)$: $T$, $x$, regime. Local primary $T$.
2. Wall temperature by bisection; $q''$, $U$.
3. Enthalpy update; shell-side $\Delta p$.
4. Midpoint (RK2) correction. Sub-steps at the regime boundaries $h_f$, $h_f + x_{do}h_{fg}$, $h_g$.

The march stops when $h_s$ reaches the outlet enthalpy; the height is the result. The shell inlet
pressure is iterated (3 passes) so that the outlet pressure equals the specification. The primary
reaches 325 °C at the top by energy conservation (closure check). A fine march ($\Delta z$ = 0.1 m)
fixes the height; the reported march uses 40 equal segments. 20, 40 and 80 segments give 18.64,
18.70 and 18.72 m against 18.72 m for the fine march.

## Weight

Dry metal: tubes, shell ($L$ + two tubesheets), two hemispherical heads, two tubesheets minus the
tube holes, support plates (25 mm, 50 % solid), plus 10 % for nozzles, skirt and internals.

## Results (from `code/sg_design.py`, 70 bar)

| Quantity | Result |
|---|---|
| (i) tubes | 14 094 |
| (ii) tube ID, wall, height | 12.93 mm, 1.473 mm, 18.7 m |
| (iii) shell ID, wall | 2.72 m, 95 mm |
| (iv) $\Delta p$ shell, tube | 0.40 bar, 0.94 bar (irreversible) |
| (v) dry weight | 357 t |

---
part: AS60R045
doc_type: datasheet
revision: 2
effective: 2026-02-01
supersedes: 1
---
# AS60R045 600 V N-channel power MOSFET (fictional part, illustrative values)
The AS60R045 targets server power supplies and solar inverters that need low conduction loss.
It is housed in a TO-247 package and qualified for industrial temperature range.

| parameter | value | unit | condition |
|---|---|---|---|
| V_DS | 600 | V | |
| R_DS(on) max | 45 | mΩ | V_GS=10V, T_j=25°C |
| I_D continuous | 46 | A | T_c=25°C |
| Q_g typical | 68 | nC | |
| T_j max | 150 | °C | |

Revision 2 corrects the gate charge value and adds the avalanche rating note.
Avoid exceeding 20 V gate-source voltage; use a gate resistor to limit dv/dt ringing.

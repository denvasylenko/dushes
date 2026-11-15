# Veltra HX Controller Parameter Reference

Firmware 2.4. Every parameter with its range, its factory default and the access level needed to change it (U = user, I = installer, S = Veltra service). For a unit on a later firmware, the release notes list the defaults that changed.

## Group 0: Basics

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P000 | Basics: maximum speed 1 | 30 to 75 | 70 | % | I |
| P001 | Basics: alarm delay 1 | 85 to 195 | 175 | s | I |
| P002 | Basics: frost limit 3 | 12 to 35 | 30 | h | I |
| P003 | Basics: night setback 3 | 5 to 38 | 30 | h | I |
| P004 | Basics: switch-over temperature 2 | 2 to 13 | 8 | K | S |
| P005 | Basics: target temperature 2 | 40 to 80 | 45 | % | I |
| P006 | Basics: curve slope 3 | 1 to 12 | 6 | K | U |
| P007 | Basics: hysteresis 3 | 6 to 51 | 51 | min | I |
| P008 | Basics: night setback 4 | 13 to 22 | 16 | h | S |
| P009 | Basics: delay after start 1 | 22 to 49 | 27 | h | S |
| P010 | Basics: curve shift 3 | 1 to 13 | 3 | K | I |
| P011 | Basics: pump overrun 2 | 135 to 185 | 160 | s | U |
| P012 | Basics: curve shift 4 | 20 to 95 | 65 | % | U |
| P013 | Basics: offset 2 | 195 to 265 | 215 | s | I |
| P014 | Basics: minimum run time 1 | 95 to 445 | 315 | s | I |
| P015 | Basics: priority 4 | 15 to 65 | 65 | % | S |
| P016 | Basics: target temperature 3 | 85 to 210 | 160 | s | I |
| P017 | Basics: priority 4 | 5 to 15 | 14 | K | U |
| P018 | Basics: frost limit 2 | 20 to 58 | 28 | degrees | I |
| P019 | Basics: offset 2 | 9 to 14 | 10 | degrees | S |
| P020 | Hydraulic scheme | 1 to 12 | 1 | - | I |
| P021 | Heat pump model | 20, 35, 50, 80 | set at the factory | - | I |
| P022 | Basics: curve shift 2 | 38 to 43 | 40 | min | I |
| P023 | Basics: valve run time 1 | 40 to 87 | 54 | min | S |
| P024 | Basics: pump overrun 3 | 38 to 69 | 47 | min | S |
| P025 | Basics: curve shift 3 | 3 to 15 | 14 | K | I |
| P026 | Basics: maximum run time 4 | 10 to 20 | 20 | % | U |
| P027 | Basics: valve run time 1 | 25 to 205 | 50 | s | I |
| P028 | Basics: pump overrun 4 | 36 to 56 | 38 | min | I |
| P029 | Basics: limit 2 | 25 to 285 | 205 | s | I |

### Group 0 in detail

**P000 Basics: maximum speed 1.** Range 30 to 75 %, default 70. Change it only together with P020. A wrong value shows as noise at night. Takes effect after the next compressor stop.

**P001 Basics: alarm delay 1.** Range 85 to 195 s, default 175. Change it in steps of one, watching P011. A value that is too low shows as fault F105. Takes effect at the next scheduled run.

**P002 Basics: frost limit 3.** Range 12 to 35 h, default 30. Lower it in steps of one, watching P021. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P003 Basics: night setback 3.** Range 5 to 38 h, default 30. Change it after checking P006. A wrong value shows as fault F419. Takes effect at the next scheduled run.

**P004 Basics: switch-over temperature 2.** Range 2 to 13 K, default 8. Raise it after checking P010. A wrong value shows as slow heating up. Takes effect after the next compressor stop.

**P005 Basics: target temperature 2.** Range 40 to 80 %, default 45. Change it only together with P007. A wrong value shows as noise at night. Takes effect at the next scheduled run.

**P006 Basics: curve slope 3.** Range 1 to 12 K, default 6. Raise it after checking P024. A value that is too high shows as a high return temperature. Takes effect at once.

**P007 Basics: hysteresis 3.** Range 6 to 51 min, default 51. Change it only together with P016. A value that is too low shows as fault F192. Takes effect at the next scheduled run.

**P008 Basics: night setback 4.** Range 13 to 22 h, default 16. Raise it in steps of one, watching P001. A value that is too high shows as slow heating up. Takes effect at once.

**P009 Basics: delay after start 1.** Range 22 to 49 h, default 27. Raise it only together with P006. A value that is too high shows as slow heating up. Takes effect after a restart of the controller.

**P010 Basics: curve shift 3.** Range 1 to 13 K, default 3. Change it after checking P029. A wrong value shows as fault F186. Takes effect at once.

**P011 Basics: pump overrun 2.** Range 135 to 185 s, default 160. Raise it only together with P017. A wrong value shows as slow heating up. Takes effect after the next compressor stop.

**P012 Basics: curve shift 4.** Range 20 to 95 %, default 65. Raise it after checking P029. A wrong value shows as long defrosts. Takes effect at once.

**P013 Basics: offset 2.** Range 195 to 265 s, default 215. Lower it in steps of one, watching P011. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P014 Basics: minimum run time 1.** Range 95 to 445 s, default 315. Lower it only together with P026. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P015 Basics: priority 4.** Range 15 to 65 %, default 65. Raise it after checking P025. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

**P016 Basics: target temperature 3.** Range 85 to 210 s, default 160. Lower it only together with P026. A value that is too low shows as slow heating up. Takes effect after a restart of the controller.

**P017 Basics: priority 4.** Range 5 to 15 K, default 14. Lower it after checking P017. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P018 Basics: frost limit 2.** Range 20 to 58 degrees, default 28. Lower it in steps of one, watching P014. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P019 Basics: offset 2.** Range 9 to 14 degrees, default 10. Change it in steps of one, watching P015. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P022 Basics: curve shift 2.** Range 38 to 43 min, default 40. Change it only together with P028. A value that is too high shows as slow heating up. Takes effect after the next compressor stop.

**P023 Basics: valve run time 1.** Range 40 to 87 min, default 54. Change it in steps of one, watching P023. A wrong value shows as higher energy use. Takes effect after the next compressor stop.

**P024 Basics: pump overrun 3.** Range 38 to 69 min, default 47. Lower it in steps of one, watching P019. A value that is too low shows as noise at night. Takes effect after the next compressor stop.

**P025 Basics: curve shift 3.** Range 3 to 15 K, default 14. Raise it in steps of one, watching P009. A wrong value shows as long defrosts. Takes effect at the next scheduled run.

**P026 Basics: maximum run time 4.** Range 10 to 20 %, default 20. Raise it only together with P012. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P027 Basics: valve run time 1.** Range 25 to 205 s, default 50. Change it after checking P012. A value that is too low shows as short cycling. Takes effect at once.

**P028 Basics: pump overrun 4.** Range 36 to 56 min, default 38. Change it after checking P013. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P029 Basics: limit 2.** Range 25 to 285 s, default 205. Raise it only together with P017. A value that is too low shows as noise at night. Takes effect at once.

## Group 1: Heating and hot water

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P100 | Heating curve: flow temperature at -10 degrees outdoor | 25 to 70 | 45 | degrees | I |
| P101 | Heating and hot water: curve slope 2 | 10 to 93 | 58 | min | I |
| P102 | Heating and hot water: ramp 3 | 1 to 33 | 19 | h | I |
| P103 | Heating and hot water: priority 4 | 5 to 12 | 10 | K | S |
| P104 | Heating and hot water: frost limit 3 | 20 to 90 | 75 | % | I |
| P105 | Heating and hot water: release temperature 2 | 6 to 27 | 8 | h | I |
| P106 | Heating and hot water: boost time 1 | 19 to 48 | 32 | h | I |
| P107 | Heating and hot water: sensor correction 3 | 3 to 12 | 9 | K | I |
| P108 | Heating and hot water: curve slope 3 | 23 to 28 | 26 | degrees | I |
| P109 | Heating and hot water: frost limit 3 | 9 to 18 | 18 | min | S |
| P110 | Domestic hot water target temperature | 40 to 60 | 50 | degrees | I |
| P111 | Heating and hot water: restart delay 2 | 25 to 40 | 40 | % | I |
| P112 | Anti-legionella target temperature | 55 to 70 | 55 | degrees | I |
| P113 | Anti-legionella program day and time | Mon to Sun, 00:00 to 23:00 | Sunday 02:00 | - | I |
| P114 | Heating and hot water: curve shift 2 | 10 to 70 | 45 | % | I |
| P115 | Heating and hot water: night setback 1 | 20 to 45 | 40 | % | I |
| P116 | Heating and hot water: priority 2 | 35 to 60 | 50 | % | I |
| P117 | Heating and hot water: target temperature 4 | 4 to 6 | 5 | K | S |
| P118 | Heating and hot water: frost limit 2 | 40 to 95 | 75 | % | I |
| P119 | Heating and hot water: priority 1 | 15 to 85 | 25 | % | I |
| P120 | Heating and hot water: minimum run time 2 | 20 to 90 | 35 | % | I |
| P121 | Heating and hot water: night setback 4 | 9 to 18 | 9 | degrees | U |
| P122 | Heating and hot water: target temperature 3 | 30 to 37 | 31 | min | U |
| P123 | Heating and hot water: minimum run time 1 | 28 to 34 | 31 | min | U |
| P124 | Heating and hot water: switch-over temperature 1 | 14 to 64 | 40 | h | I |
| P125 | Heating and hot water: switch-over temperature 2 | 23 to 54 | 30 | degrees | I |
| P126 | Heating and hot water: pump overrun 2 | 14 to 40 | 29 | h | I |
| P127 | Heating and hot water: boost time 1 | 115 to 390 | 140 | s | I |
| P128 | Heating and hot water: delay after start 4 | 11 to 36 | 23 | h | I |
| P129 | Heating and hot water: target temperature 2 | 15 to 50 | 35 | % | I |
| P130 | Heating and hot water: night setback 1 | 140 to 425 | 140 | s | I |
| P131 | Heating and hot water: curve slope 3 | 1 to 4 | 3 | K | U |
| P132 | Heating and hot water: night setback 2 | 10 to 104 | 73 | min | S |
| P133 | Heating and hot water: delay after start 2 | 9 to 13 | 10 | min | U |
| P134 | Heating and hot water: sensor correction 2 | 27 to 106 | 84 | min | I |
| P135 | Heating and hot water: maximum run time 3 | 2 to 63 | 50 | h | U |
| P136 | Heating and hot water: hysteresis 1 | 9 to 21 | 11 | h | I |
| P137 | Heating and hot water: valve run time 3 | 13 to 20 | 13 | degrees | U |
| P138 | Heating and hot water: valve run time 3 | 5 to 15 | 9 | K | I |
| P139 | Heating and hot water: offset 4 | 20 to 52 | 43 | degrees | U |
| P140 | Heating and hot water: delay after start 1 | 3 to 8 | 5 | K | U |
| P141 | Heating and hot water: ramp 1 | 40 to 70 | 60 | % | I |
| P142 | Heating and hot water: alarm delay 2 | 2 to 5 | 3 | K | I |
| P143 | Heating and hot water: release temperature 1 | 36 to 91 | 43 | min | I |
| P144 | Heating and hot water: valve run time 2 | 15 to 85 | 85 | % | S |
| P145 | Heating and hot water: ramp 3 | 2 to 13 | 11 | K | I |
| P146 | Heating and hot water: release temperature 4 | 180 to 450 | 245 | s | U |
| P147 | Heating and hot water: target temperature 3 | 9 to 40 | 38 | h | I |
| P148 | Heating and hot water: alarm delay 2 | 9 to 55 | 15 | h | I |
| P149 | Heating and hot water: hysteresis 2 | 15 to 95 | 60 | % | U |
| P150 | Heating and hot water: offset 4 | 20 to 200 | 145 | s | S |
| P151 | Heating and hot water: test interval 2 | 6 to 67 | 52 | degrees | I |
| P152 | Heating and hot water: sensor correction 2 | 23 to 46 | 37 | h | I |
| P153 | Heating and hot water: sensor correction 2 | 35 to 85 | 40 | % | I |
| P154 | Heating and hot water: maximum run time 3 | 17 to 27 | 24 | min | I |
| P155 | Heating and hot water: curve shift 4 | 20 to 45 | 42 | h | S |
| P156 | Heating and hot water: restart delay 1 | 2 to 14 | 13 | K | I |
| P157 | Heating and hot water: curve slope 2 | 5 to 14 | 10 | K | S |
| P158 | Heating and hot water: hysteresis 1 | 30 to 75 | 53 | min | S |
| P159 | Heating and hot water: frost limit 4 | 30 to 75 | 35 | % | S |
| P160 | Heating and hot water: target temperature 3 | 30 to 70 | 35 | % | U |
| P161 | Heating and hot water: offset 2 | 26 to 52 | 31 | degrees | I |
| P162 | Heating and hot water: curve shift 4 | 35 to 50 | 50 | % | I |
| P163 | Heating and hot water: pump overrun 3 | 6 to 44 | 10 | h | I |
| P164 | Heating and hot water: pump overrun 2 | 100 to 535 | 355 | s | I |
| P165 | Heating and hot water: priority 4 | 5 to 10 | 10 | K | S |
| P166 | Heating and hot water: minimum speed 3 | 10 to 85 | 75 | % | S |
| P167 | Heating and hot water: release temperature 3 | 9 to 38 | 37 | min | S |
| P168 | Heating and hot water: target temperature 1 | 2 to 62 | 18 | h | U |
| P169 | Heating and hot water: hysteresis 3 | 12 to 27 | 15 | degrees | S |

### Group 1 in detail

**P101 Heating and hot water: curve slope 2.** Range 10 to 93 min, default 58. Change it after checking P159. A value that is too low shows as short cycling. Takes effect at once.

**P102 Heating and hot water: ramp 3.** Range 1 to 33 h, default 19. Lower it after checking P106. A wrong value shows as slow heating up. Takes effect after the next compressor stop.

**P103 Heating and hot water: priority 4.** Range 5 to 12 K, default 10. Lower it after checking P104. A value that is too low shows as short cycling. Takes effect at the next scheduled run.

**P104 Heating and hot water: frost limit 3.** Range 20 to 90 %, default 75. Lower it in steps of one, watching P130. A value that is too high shows as short cycling. Takes effect at once.

**P105 Heating and hot water: release temperature 2.** Range 6 to 27 h, default 8. Lower it in steps of one, watching P155. A value that is too high shows as fault F154. Takes effect at once.

**P106 Heating and hot water: boost time 1.** Range 19 to 48 h, default 32. Raise it in steps of one, watching P145. A value that is too low shows as fault F338. Takes effect after a restart of the controller.

**P107 Heating and hot water: sensor correction 3.** Range 3 to 12 K, default 9. Change it after checking P147. A wrong value shows as slow heating up. Takes effect after the next compressor stop.

**P108 Heating and hot water: curve slope 3.** Range 23 to 28 degrees, default 26. Raise it after checking P146. A wrong value shows as fault F215. Takes effect at the next scheduled run.

**P109 Heating and hot water: frost limit 3.** Range 9 to 18 min, default 18. Raise it only together with P165. A wrong value shows as noise at night. Takes effect at the next scheduled run.

**P111 Heating and hot water: restart delay 2.** Range 25 to 40 %, default 40. Change it in steps of one, watching P100. A wrong value shows as higher energy use. Takes effect after a restart of the controller.

**P114 Heating and hot water: curve shift 2.** Range 10 to 70 %, default 45. Raise it after checking P134. A wrong value shows as a high return temperature. Takes effect at once.

**P115 Heating and hot water: night setback 1.** Range 20 to 45 %, default 40. Change it only together with P103. A wrong value shows as fault F189. Takes effect after the next compressor stop.

**P116 Heating and hot water: priority 2.** Range 35 to 60 %, default 50. Lower it in steps of one, watching P157. A wrong value shows as slow heating up. Takes effect at once.

**P117 Heating and hot water: target temperature 4.** Range 4 to 6 K, default 5. Lower it in steps of one, watching P115. A value that is too high shows as slow heating up. Takes effect at the next scheduled run.

**P118 Heating and hot water: frost limit 2.** Range 40 to 95 %, default 75. Lower it only together with P167. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P119 Heating and hot water: priority 1.** Range 15 to 85 %, default 25. Lower it only together with P110. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P120 Heating and hot water: minimum run time 2.** Range 20 to 90 %, default 35. Raise it after checking P126. A value that is too low shows as higher energy use. Takes effect after a restart of the controller.

**P121 Heating and hot water: night setback 4.** Range 9 to 18 degrees, default 9. Change it after checking P103. A value that is too low shows as long defrosts. Takes effect after a restart of the controller.

**P122 Heating and hot water: target temperature 3.** Range 30 to 37 min, default 31. Raise it only together with P113. A value that is too high shows as higher energy use. Takes effect at once.

**P123 Heating and hot water: minimum run time 1.** Range 28 to 34 min, default 31. Change it only together with P145. A value that is too low shows as short cycling. Takes effect after the next compressor stop.

**P124 Heating and hot water: switch-over temperature 1.** Range 14 to 64 h, default 40. Change it after checking P153. A wrong value shows as noise at night. Takes effect after the next compressor stop.

**P125 Heating and hot water: switch-over temperature 2.** Range 23 to 54 degrees, default 30. Change it after checking P127. A wrong value shows as short cycling. Takes effect at the next scheduled run.

**P126 Heating and hot water: pump overrun 2.** Range 14 to 40 h, default 29. Change it in steps of one, watching P117. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

**P127 Heating and hot water: boost time 1.** Range 115 to 390 s, default 140. Raise it after checking P117. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P128 Heating and hot water: delay after start 4.** Range 11 to 36 h, default 23. Raise it only together with P169. A value that is too high shows as higher energy use. Takes effect at once.

**P129 Heating and hot water: target temperature 2.** Range 15 to 50 %, default 35. Raise it after checking P111. A value that is too low shows as short cycling. Takes effect after a restart of the controller.

**P130 Heating and hot water: night setback 1.** Range 140 to 425 s, default 140. Lower it only together with P115. A value that is too low shows as higher energy use. Takes effect at once.

**P131 Heating and hot water: curve slope 3.** Range 1 to 4 K, default 3. Raise it only together with P166. A value that is too high shows as slow heating up. Takes effect at the next scheduled run.

**P132 Heating and hot water: night setback 2.** Range 10 to 104 min, default 73. Change it only together with P134. A value that is too high shows as fault F163. Takes effect at the next scheduled run.

**P133 Heating and hot water: delay after start 2.** Range 9 to 13 min, default 10. Raise it after checking P136. A value that is too low shows as a high return temperature. Takes effect at the next scheduled run.

**P134 Heating and hot water: sensor correction 2.** Range 27 to 106 min, default 84. Lower it only together with P159. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P135 Heating and hot water: maximum run time 3.** Range 2 to 63 h, default 50. Lower it after checking P102. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P136 Heating and hot water: hysteresis 1.** Range 9 to 21 h, default 11. Change it after checking P153. A value that is too high shows as long defrosts. Takes effect after a restart of the controller.

**P137 Heating and hot water: valve run time 3.** Range 13 to 20 degrees, default 13. Change it only together with P115. A value that is too low shows as slow heating up. Takes effect after the next compressor stop.

**P138 Heating and hot water: valve run time 3.** Range 5 to 15 K, default 9. Raise it only together with P143. A wrong value shows as long defrosts. Takes effect at once.

**P139 Heating and hot water: offset 4.** Range 20 to 52 degrees, default 43. Change it in steps of one, watching P132. A value that is too low shows as short cycling. Takes effect at once.

**P140 Heating and hot water: delay after start 1.** Range 3 to 8 K, default 5. Raise it after checking P110. A value that is too high shows as short cycling. Takes effect at the next scheduled run.

**P141 Heating and hot water: ramp 1.** Range 40 to 70 %, default 60. Change it in steps of one, watching P127. A value that is too high shows as slow heating up. Takes effect after the next compressor stop.

**P142 Heating and hot water: alarm delay 2.** Range 2 to 5 K, default 3. Lower it in steps of one, watching P141. A value that is too low shows as higher energy use. Takes effect at the next scheduled run.

**P143 Heating and hot water: release temperature 1.** Range 36 to 91 min, default 43. Raise it only together with P127. A wrong value shows as short cycling. Takes effect at once.

**P144 Heating and hot water: valve run time 2.** Range 15 to 85 %, default 85. Lower it in steps of one, watching P103. A value that is too high shows as higher energy use. Takes effect after the next compressor stop.

**P145 Heating and hot water: ramp 3.** Range 2 to 13 K, default 11. Lower it in steps of one, watching P106. A value that is too low shows as fault F139. Takes effect after a restart of the controller.

**P146 Heating and hot water: release temperature 4.** Range 180 to 450 s, default 245. Change it only together with P165. A value that is too high shows as short cycling. Takes effect after the next compressor stop.

**P147 Heating and hot water: target temperature 3.** Range 9 to 40 h, default 38. Raise it in steps of one, watching P138. A value that is too high shows as a high return temperature. Takes effect after the next compressor stop.

**P148 Heating and hot water: alarm delay 2.** Range 9 to 55 h, default 15. Raise it in steps of one, watching P103. A wrong value shows as long defrosts. Takes effect after a restart of the controller.

**P149 Heating and hot water: hysteresis 2.** Range 15 to 95 %, default 60. Lower it in steps of one, watching P133. A value that is too high shows as fault F254. Takes effect after the next compressor stop.

**P150 Heating and hot water: offset 4.** Range 20 to 200 s, default 145. Raise it after checking P148. A value that is too low shows as long defrosts. Takes effect after a restart of the controller.

**P151 Heating and hot water: test interval 2.** Range 6 to 67 degrees, default 52. Change it only together with P119. A value that is too low shows as short cycling. Takes effect after the next compressor stop.

**P152 Heating and hot water: sensor correction 2.** Range 23 to 46 h, default 37. Change it in steps of one, watching P152. A value that is too high shows as short cycling. Takes effect after a restart of the controller.

**P153 Heating and hot water: sensor correction 2.** Range 35 to 85 %, default 40. Change it after checking P123. A value that is too high shows as fault F218. Takes effect after the next compressor stop.

**P154 Heating and hot water: maximum run time 3.** Range 17 to 27 min, default 24. Raise it only together with P128. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P155 Heating and hot water: curve shift 4.** Range 20 to 45 h, default 42. Raise it in steps of one, watching P131. A value that is too high shows as short cycling. Takes effect after the next compressor stop.

**P156 Heating and hot water: restart delay 1.** Range 2 to 14 K, default 13. Change it only together with P142. A value that is too low shows as fault F221. Takes effect after a restart of the controller.

**P157 Heating and hot water: curve slope 2.** Range 5 to 14 K, default 10. Lower it after checking P123. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P158 Heating and hot water: hysteresis 1.** Range 30 to 75 min, default 53. Raise it after checking P168. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P159 Heating and hot water: frost limit 4.** Range 30 to 75 %, default 35. Raise it after checking P165. A value that is too high shows as slow heating up. Takes effect after the next compressor stop.

**P160 Heating and hot water: target temperature 3.** Range 30 to 70 %, default 35. Lower it in steps of one, watching P105. A value that is too low shows as slow heating up. Takes effect after the next compressor stop.

**P161 Heating and hot water: offset 2.** Range 26 to 52 degrees, default 31. Change it after checking P144. A value that is too high shows as long defrosts. Takes effect at once.

**P162 Heating and hot water: curve shift 4.** Range 35 to 50 %, default 50. Change it in steps of one, watching P152. A wrong value shows as short cycling. Takes effect after the next compressor stop.

**P163 Heating and hot water: pump overrun 3.** Range 6 to 44 h, default 10. Raise it only together with P124. A wrong value shows as higher energy use. Takes effect after the next compressor stop.

**P164 Heating and hot water: pump overrun 2.** Range 100 to 535 s, default 355. Lower it after checking P115. A wrong value shows as long defrosts. Takes effect after a restart of the controller.

**P165 Heating and hot water: priority 4.** Range 5 to 10 K, default 10. Raise it in steps of one, watching P158. A value that is too low shows as higher energy use. Takes effect after the next compressor stop.

**P166 Heating and hot water: minimum speed 3.** Range 10 to 85 %, default 75. Lower it only together with P135. A wrong value shows as noise at night. Takes effect after a restart of the controller.

**P167 Heating and hot water: release temperature 3.** Range 9 to 38 min, default 37. Lower it after checking P100. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

**P168 Heating and hot water: target temperature 1.** Range 2 to 62 h, default 18. Lower it only together with P117. A value that is too low shows as a high return temperature. Takes effect after the next compressor stop.

**P169 Heating and hot water: hysteresis 3.** Range 12 to 27 degrees, default 15. Lower it only together with P167. A value that is too low shows as higher energy use. Takes effect after the next compressor stop.

## Group 2: Compressor and defrost

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P200 | Compressor and defrost: curve shift 3 | 12 to 36 | 19 | degrees | I |
| P201 | Compressor and defrost: alarm delay 1 | 19 to 27 | 21 | degrees | I |
| P202 | Compressor and defrost: alarm delay 2 | 80 to 315 | 315 | s | I |
| P203 | Compressor and defrost: pump overrun 3 | 15 to 25 | 20 | % | I |
| P204 | Compressor and defrost: priority 2 | 175 to 210 | 200 | s | I |
| P205 | Minimum compressor off time | 3 to 15 | 5 | min | I |
| P206 | Compressor and defrost: test interval 4 | 2 to 14 | 3 | K | S |
| P207 | Compressor and defrost: hysteresis 2 | 6 to 40 | 6 | degrees | I |
| P208 | Compressor and defrost: minimum speed 4 | 135 to 385 | 280 | s | I |
| P209 | Compressor and defrost: minimum run time 1 | 14 to 45 | 24 | h | I |
| P210 | Defrost: minimum interval between two defrosts | 20 to 90 | 35 | min | I |
| P211 | Compressor and defrost: target temperature 3 | 5 to 8 | 7 | h | U |
| P212 | Compressor and defrost: priority 2 | 23 to 66 | 44 | h | I |
| P213 | Compressor and defrost: offset 4 | 4 to 12 | 10 | K | I |
| P214 | Compressor and defrost: boost time 1 | 24 to 40 | 36 | degrees | I |
| P215 | Compressor and defrost: pump overrun 3 | 31 to 58 | 48 | min | I |
| P216 | Compressor and defrost: curve shift 3 | 11 to 40 | 34 | h | I |
| P217 | Compressor and defrost: minimum speed 4 | 2 to 14 | 7 | K | I |
| P218 | Compressor and defrost: ramp 4 | 1 to 12 | 6 | K | I |
| P219 | Compressor and defrost: curve shift 4 | 4 to 7 | 7 | K | I |
| P220 | Compressor and defrost: frost limit 1 | 13 to 45 | 32 | degrees | I |
| P221 | Compressor and defrost: hysteresis 3 | 37 to 98 | 87 | min | I |
| P222 | Compressor and defrost: alarm delay 1 | 5 to 60 | 56 | degrees | U |
| P223 | Compressor and defrost: sensor correction 2 | 16 to 50 | 21 | degrees | S |
| P224 | Compressor and defrost: valve run time 4 | 9 to 47 | 20 | min | S |
| P225 | Compressor and defrost: maximum run time 4 | 6 to 61 | 50 | degrees | S |
| P226 | Compressor and defrost: alarm delay 1 | 175 to 200 | 190 | s | S |
| P227 | Compressor and defrost: alarm delay 4 | 20 to 84 | 28 | min | I |
| P228 | Compressor and defrost: release temperature 3 | 30 to 40 | 30 | min | I |
| P229 | Compressor and defrost: maximum run time 4 | 13 to 63 | 58 | degrees | S |
| P230 | Compressor and defrost: sensor correction 3 | 115 to 340 | 125 | s | I |
| P231 | Compressor and defrost: delay after start 2 | 12 to 57 | 30 | min | I |
| P232 | Compressor and defrost: limit 3 | 26 to 67 | 28 | min | U |
| P233 | Compressor and defrost: pump overrun 1 | 2 to 68 | 46 | h | I |
| P234 | Compressor and defrost: minimum run time 3 | 165 to 250 | 185 | s | I |
| P235 | Compressor and defrost: frost limit 4 | 35 to 90 | 80 | % | I |
| P236 | Compressor and defrost: limit 1 | 22 to 26 | 24 | degrees | I |
| P237 | Compressor and defrost: test interval 4 | 30 to 70 | 65 | % | U |
| P238 | Compressor and defrost: frost limit 1 | 35 to 95 | 45 | % | I |
| P239 | Compressor and defrost: minimum speed 4 | 6 to 23 | 19 | min | I |
| P240 | Compressor and defrost: limit 2 | 65 to 340 | 175 | s | I |
| P241 | Compressor and defrost: priority 3 | 38 to 97 | 39 | min | U |
| P242 | Compressor and defrost: switch-over temperature 3 | 12 to 34 | 17 | degrees | U |
| P243 | Compressor and defrost: release temperature 4 | 35 to 65 | 50 | % | I |
| P244 | Compressor and defrost: curve slope 4 | 2 to 51 | 25 | min | S |
| P245 | Compressor and defrost: test interval 4 | 38 to 79 | 46 | min | I |
| P246 | Compressor and defrost: ramp 1 | 22 to 24 | 23 | h | S |
| P247 | Compressor and defrost: minimum run time 2 | 15 to 18 | 18 | degrees | I |
| P248 | Compressor and defrost: night setback 3 | 40 to 75 | 45 | % | I |
| P249 | Compressor and defrost: minimum speed 2 | 31 to 71 | 34 | min | U |
| P250 | Compressor and defrost: maximum speed 4 | 19 to 26 | 20 | degrees | I |
| P251 | Compressor and defrost: curve slope 4 | 22 to 58 | 54 | h | I |
| P252 | Compressor and defrost: release temperature 3 | 14 to 36 | 16 | h | I |
| P253 | Compressor and defrost: night setback 3 | 15 to 76 | 54 | min | S |
| P254 | Compressor and defrost: target temperature 3 | 3 to 15 | 8 | K | I |
| P255 | Compressor and defrost: minimum speed 2 | 10 to 25 | 20 | % | S |
| P256 | Compressor and defrost: limit 1 | 4 to 15 | 10 | K | I |
| P257 | Compressor and defrost: offset 2 | 1 to 11 | 1 | K | I |
| P258 | Compressor and defrost: boost time 3 | 9 to 32 | 11 | h | I |
| P259 | Compressor and defrost: restart delay 1 | 30 to 95 | 30 | % | I |
| P260 | Compressor and defrost: ramp 2 | 18 to 69 | 27 | degrees | U |
| P261 | Compressor and defrost: offset 2 | 4 to 9 | 7 | K | I |
| P262 | Compressor and defrost: alarm delay 3 | 4 to 9 | 4 | K | I |
| P263 | Compressor and defrost: ramp 4 | 8 to 51 | 23 | min | I |
| P264 | Compressor and defrost: offset 1 | 20 to 440 | 215 | s | I |
| P265 | Compressor and defrost: frost limit 1 | 3 to 68 | 52 | h | I |
| P266 | Compressor and defrost: minimum speed 2 | 85 to 310 | 85 | s | I |
| P267 | Compressor and defrost: hysteresis 1 | 30 to 40 | 30 | % | I |
| P268 | Compressor and defrost: limit 1 | 16 to 63 | 25 | min | U |
| P269 | Compressor and defrost: frost limit 2 | 25 to 47 | 30 | degrees | I |

### Group 2 in detail

**P200 Compressor and defrost: curve shift 3.** Range 12 to 36 degrees, default 19. Lower it after checking P251. A value that is too high shows as slow heating up. Takes effect after the next compressor stop.

**P201 Compressor and defrost: alarm delay 1.** Range 19 to 27 degrees, default 21. Raise it only together with P224. A value that is too high shows as short cycling. Takes effect after a restart of the controller.

**P202 Compressor and defrost: alarm delay 2.** Range 80 to 315 s, default 315. Lower it after checking P208. A value that is too low shows as slow heating up. Takes effect at once.

**P203 Compressor and defrost: pump overrun 3.** Range 15 to 25 %, default 20. Change it in steps of one, watching P269. A wrong value shows as short cycling. Takes effect after the next compressor stop.

**P204 Compressor and defrost: priority 2.** Range 175 to 210 s, default 200. Change it only together with P212. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P206 Compressor and defrost: test interval 4.** Range 2 to 14 K, default 3. Raise it after checking P210. A wrong value shows as long defrosts. Takes effect at once.

**P207 Compressor and defrost: hysteresis 2.** Range 6 to 40 degrees, default 6. Raise it after checking P230. A wrong value shows as long defrosts. Takes effect after a restart of the controller.

**P208 Compressor and defrost: minimum speed 4.** Range 135 to 385 s, default 280. Raise it only together with P252. A wrong value shows as higher energy use. Takes effect at once.

**P209 Compressor and defrost: minimum run time 1.** Range 14 to 45 h, default 24. Change it in steps of one, watching P227. A wrong value shows as fault F353. Takes effect at the next scheduled run.

**P211 Compressor and defrost: target temperature 3.** Range 5 to 8 h, default 7. Change it after checking P256. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

**P212 Compressor and defrost: priority 2.** Range 23 to 66 h, default 44. Raise it only together with P206. A value that is too high shows as short cycling. Takes effect after a restart of the controller.

**P213 Compressor and defrost: offset 4.** Range 4 to 12 K, default 10. Raise it after checking P244. A wrong value shows as noise at night. Takes effect after a restart of the controller.

**P214 Compressor and defrost: boost time 1.** Range 24 to 40 degrees, default 36. Change it in steps of one, watching P224. A value that is too high shows as noise at night. Takes effect after the next compressor stop.

**P215 Compressor and defrost: pump overrun 3.** Range 31 to 58 min, default 48. Raise it after checking P217. A wrong value shows as noise at night. Takes effect after the next compressor stop.

**P216 Compressor and defrost: curve shift 3.** Range 11 to 40 h, default 34. Change it after checking P251. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P217 Compressor and defrost: minimum speed 4.** Range 2 to 14 K, default 7. Raise it only together with P214. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P218 Compressor and defrost: ramp 4.** Range 1 to 12 K, default 6. Lower it after checking P258. A value that is too high shows as slow heating up. Takes effect at once.

**P219 Compressor and defrost: curve shift 4.** Range 4 to 7 K, default 7. Raise it in steps of one, watching P216. A value that is too high shows as slow heating up. Takes effect at once.

**P220 Compressor and defrost: frost limit 1.** Range 13 to 45 degrees, default 32. Change it only together with P201. A value that is too high shows as higher energy use. Takes effect at the next scheduled run.

**P221 Compressor and defrost: hysteresis 3.** Range 37 to 98 min, default 87. Change it after checking P245. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P222 Compressor and defrost: alarm delay 1.** Range 5 to 60 degrees, default 56. Raise it in steps of one, watching P209. A value that is too low shows as higher energy use. Takes effect at the next scheduled run.

**P223 Compressor and defrost: sensor correction 2.** Range 16 to 50 degrees, default 21. Change it only together with P259. A value that is too low shows as slow heating up. Takes effect at once.

**P224 Compressor and defrost: valve run time 4.** Range 9 to 47 min, default 20. Change it in steps of one, watching P228. A value that is too low shows as noise at night. Takes effect at the next scheduled run.

**P225 Compressor and defrost: maximum run time 4.** Range 6 to 61 degrees, default 50. Raise it only together with P207. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P226 Compressor and defrost: alarm delay 1.** Range 175 to 200 s, default 190. Raise it in steps of one, watching P234. A value that is too high shows as short cycling. Takes effect after the next compressor stop.

**P227 Compressor and defrost: alarm delay 4.** Range 20 to 84 min, default 28. Raise it only together with P238. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P228 Compressor and defrost: release temperature 3.** Range 30 to 40 min, default 30. Raise it in steps of one, watching P221. A wrong value shows as noise at night. Takes effect after a restart of the controller.

**P229 Compressor and defrost: maximum run time 4.** Range 13 to 63 degrees, default 58. Change it only together with P214. A value that is too low shows as short cycling. Takes effect at once.

**P230 Compressor and defrost: sensor correction 3.** Range 115 to 340 s, default 125. Raise it only together with P206. A value that is too low shows as fault F198. Takes effect after the next compressor stop.

**P231 Compressor and defrost: delay after start 2.** Range 12 to 57 min, default 30. Raise it only together with P235. A value that is too low shows as noise at night. Takes effect at the next scheduled run.

**P232 Compressor and defrost: limit 3.** Range 26 to 67 min, default 28. Change it only together with P207. A value that is too low shows as slow heating up. Takes effect after the next compressor stop.

**P233 Compressor and defrost: pump overrun 1.** Range 2 to 68 h, default 46. Raise it in steps of one, watching P231. A wrong value shows as fault F109. Takes effect after the next compressor stop.

**P234 Compressor and defrost: minimum run time 3.** Range 165 to 250 s, default 185. Change it only together with P229. A wrong value shows as short cycling. Takes effect at the next scheduled run.

**P235 Compressor and defrost: frost limit 4.** Range 35 to 90 %, default 80. Change it after checking P209. A wrong value shows as noise at night. Takes effect at once.

**P236 Compressor and defrost: limit 1.** Range 22 to 26 degrees, default 24. Raise it in steps of one, watching P212. A wrong value shows as fault F289. Takes effect after the next compressor stop.

**P237 Compressor and defrost: test interval 4.** Range 30 to 70 %, default 65. Change it only together with P236. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P238 Compressor and defrost: frost limit 1.** Range 35 to 95 %, default 45. Change it after checking P223. A value that is too low shows as slow heating up. Takes effect after a restart of the controller.

**P239 Compressor and defrost: minimum speed 4.** Range 6 to 23 min, default 19. Change it in steps of one, watching P253. A value that is too high shows as a high return temperature. Takes effect after the next compressor stop.

**P240 Compressor and defrost: limit 2.** Range 65 to 340 s, default 175. Change it in steps of one, watching P253. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P241 Compressor and defrost: priority 3.** Range 38 to 97 min, default 39. Change it in steps of one, watching P252. A value that is too high shows as short cycling. Takes effect after the next compressor stop.

**P242 Compressor and defrost: switch-over temperature 3.** Range 12 to 34 degrees, default 17. Change it only together with P230. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P243 Compressor and defrost: release temperature 4.** Range 35 to 65 %, default 50. Lower it after checking P231. A wrong value shows as noise at night. Takes effect after the next compressor stop.

**P244 Compressor and defrost: curve slope 4.** Range 2 to 51 min, default 25. Change it in steps of one, watching P222. A value that is too low shows as fault F324. Takes effect after a restart of the controller.

**P245 Compressor and defrost: test interval 4.** Range 38 to 79 min, default 46. Raise it after checking P219. A value that is too low shows as noise at night. Takes effect after the next compressor stop.

**P246 Compressor and defrost: ramp 1.** Range 22 to 24 h, default 23. Lower it in steps of one, watching P250. A wrong value shows as short cycling. Takes effect at the next scheduled run.

**P247 Compressor and defrost: minimum run time 2.** Range 15 to 18 degrees, default 18. Change it in steps of one, watching P253. A value that is too low shows as short cycling. Takes effect after a restart of the controller.

**P248 Compressor and defrost: night setback 3.** Range 40 to 75 %, default 45. Lower it after checking P221. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P249 Compressor and defrost: minimum speed 2.** Range 31 to 71 min, default 34. Change it only together with P269. A value that is too high shows as higher energy use. Takes effect after a restart of the controller.

**P250 Compressor and defrost: maximum speed 4.** Range 19 to 26 degrees, default 20. Lower it only together with P215. A value that is too high shows as fault F361. Takes effect at once.

**P251 Compressor and defrost: curve slope 4.** Range 22 to 58 h, default 54. Raise it in steps of one, watching P233. A value that is too low shows as a high return temperature. Takes effect after a restart of the controller.

**P252 Compressor and defrost: release temperature 3.** Range 14 to 36 h, default 16. Raise it after checking P225. A wrong value shows as noise at night. Takes effect at the next scheduled run.

**P253 Compressor and defrost: night setback 3.** Range 15 to 76 min, default 54. Lower it after checking P248. A value that is too high shows as short cycling. Takes effect at once.

**P254 Compressor and defrost: target temperature 3.** Range 3 to 15 K, default 8. Change it after checking P220. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P255 Compressor and defrost: minimum speed 2.** Range 10 to 25 %, default 20. Change it in steps of one, watching P263. A wrong value shows as higher energy use. Takes effect at the next scheduled run.

**P256 Compressor and defrost: limit 1.** Range 4 to 15 K, default 10. Raise it in steps of one, watching P254. A wrong value shows as fault F279. Takes effect after the next compressor stop.

**P257 Compressor and defrost: offset 2.** Range 1 to 11 K, default 1. Raise it in steps of one, watching P246. A value that is too low shows as higher energy use. Takes effect at the next scheduled run.

**P258 Compressor and defrost: boost time 3.** Range 9 to 32 h, default 11. Lower it in steps of one, watching P201. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P259 Compressor and defrost: restart delay 1.** Range 30 to 95 %, default 30. Change it in steps of one, watching P230. A value that is too high shows as fault F338. Takes effect after a restart of the controller.

**P260 Compressor and defrost: ramp 2.** Range 18 to 69 degrees, default 27. Raise it in steps of one, watching P205. A value that is too low shows as slow heating up. Takes effect after the next compressor stop.

**P261 Compressor and defrost: offset 2.** Range 4 to 9 K, default 7. Lower it after checking P221. A wrong value shows as long defrosts. Takes effect at once.

**P262 Compressor and defrost: alarm delay 3.** Range 4 to 9 K, default 4. Lower it only together with P219. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P263 Compressor and defrost: ramp 4.** Range 8 to 51 min, default 23. Change it in steps of one, watching P256. A value that is too low shows as slow heating up. Takes effect after a restart of the controller.

**P264 Compressor and defrost: offset 1.** Range 20 to 440 s, default 215. Raise it only together with P241. A value that is too low shows as long defrosts. Takes effect at once.

**P265 Compressor and defrost: frost limit 1.** Range 3 to 68 h, default 52. Raise it in steps of one, watching P254. A value that is too low shows as slow heating up. Takes effect at the next scheduled run.

**P266 Compressor and defrost: minimum speed 2.** Range 85 to 310 s, default 85. Lower it only together with P223. A value that is too low shows as short cycling. Takes effect at the next scheduled run.

**P267 Compressor and defrost: hysteresis 1.** Range 30 to 40 %, default 30. Change it only together with P247. A wrong value shows as higher energy use. Takes effect after the next compressor stop.

**P268 Compressor and defrost: limit 1.** Range 16 to 63 min, default 25. Lower it after checking P244. A value that is too high shows as fault F134. Takes effect at the next scheduled run.

**P269 Compressor and defrost: frost limit 2.** Range 25 to 47 degrees, default 30. Change it in steps of one, watching P264. A wrong value shows as fault F263. Takes effect at the next scheduled run.

## Group 3: Schedules, quiet mode, utility

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P300 | Schedules: minimum speed 4 | 3 to 8 | 3 | K | I |
| P301 | Schedules: offset 4 | 19 to 40 | 31 | min | I |
| P302 | Schedules: offset 2 | 12 to 99 | 87 | min | I |
| P303 | Schedules: night setback 3 | 20 to 55 | 35 | % | I |
| P304 | Schedules: boost time 2 | 12 to 34 | 19 | degrees | S |
| P305 | Schedules: hysteresis 2 | 195 to 380 | 260 | s | S |
| P306 | Schedules: curve shift 1 | 30 to 45 | 30 | % | I |
| P307 | Schedules: maximum run time 2 | 14 to 56 | 54 | degrees | U |
| P308 | Schedules: valve run time 4 | 19 to 46 | 32 | degrees | S |
| P309 | Schedules: pump overrun 4 | 21 to 70 | 21 | degrees | I |
| P310 | Schedules: alarm delay 4 | 5 to 7 | 6 | K | I |
| P311 | Schedules: minimum speed 2 | 2 to 13 | 2 | K | I |
| P312 | Schedules: minimum run time 1 | 20 to 57 | 29 | degrees | I |
| P313 | Schedules: limit 1 | 1 to 10 | 3 | K | I |
| P314 | Schedules: night setback 3 | 120 to 430 | 285 | s | U |
| P315 | Schedules: ramp 1 | 22 to 61 | 61 | degrees | I |
| P316 | Schedules: ramp 3 | 2 to 7 | 4 | K | I |
| P317 | Schedules: priority 4 | 180 to 265 | 250 | s | S |
| P318 | Quiet mode: maximum fan speed | 30 to 80 | 30 | % | I |
| P319 | Schedules: maximum speed 2 | 10 to 20 | 10 | % | S |
| P320 | Schedules: maximum run time 3 | 35 to 100 | 95 | % | I |
| P321 | Schedules: test interval 3 | 23 to 91 | 49 | min | U |
| P322 | Schedules: minimum run time 2 | 145 to 390 | 200 | s | S |
| P323 | Schedules: curve slope 3 | 5 to 11 | 6 | K | I |
| P324 | Schedules: valve run time 4 | 26 to 31 | 26 | degrees | I |
| P325 | Schedules: release temperature 4 | 17 to 35 | 19 | degrees | S |
| P326 | Schedules: valve run time 1 | 12 to 14 | 13 | h | U |
| P327 | Schedules: test interval 1 | 7 to 26 | 7 | h | I |
| P328 | Schedules: ramp 3 | 34 to 89 | 36 | min | I |
| P329 | Schedules: pump overrun 2 | 18 to 72 | 69 | min | I |
| P330 | Schedules: alarm delay 3 | 7 to 16 | 16 | degrees | I |
| P331 | Schedules: valve run time 3 | 4 to 14 | 10 | K | I |
| P332 | Schedules: pump overrun 4 | 75 to 600 | 410 | s | I |
| P333 | Schedules: ramp 3 | 33 to 119 | 48 | min | S |
| P334 | Schedules: curve slope 4 | 19 to 27 | 26 | h | I |
| P335 | Schedules: night setback 2 | 17 to 66 | 23 | degrees | I |
| P336 | Schedules: curve shift 4 | 45 to 75 | 55 | s | I |
| P337 | Schedules: curve shift 1 | 3 to 55 | 51 | h | I |
| P338 | Schedules: curve shift 1 | 19 to 54 | 36 | h | I |
| P339 | Schedules: offset 1 | 3 to 15 | 8 | K | U |
| P340 | Schedules: maximum speed 1 | 6 to 58 | 31 | h | S |
| P341 | Schedules: test interval 1 | 13 to 55 | 47 | degrees | U |
| P342 | Schedules: valve run time 3 | 150 to 320 | 235 | s | U |
| P343 | Schedules: boost time 4 | 27 to 119 | 92 | min | I |
| P344 | Schedules: sensor correction 4 | 20 to 40 | 25 | h | U |
| P345 | Schedules: sensor correction 2 | 135 to 220 | 135 | s | I |
| P346 | Schedules: valve run time 2 | 23 to 47 | 36 | h | I |
| P347 | Schedules: curve slope 2 | 25 to 98 | 73 | min | U |
| P348 | Schedules: switch-over temperature 2 | 16 to 48 | 24 | min | I |
| P349 | Schedules: restart delay 2 | 15 to 100 | 25 | % | S |

### Group 3 in detail

**P300 Schedules: minimum speed 4.** Range 3 to 8 K, default 3. Lower it only together with P339. A wrong value shows as short cycling. Takes effect at the next scheduled run.

**P301 Schedules: offset 4.** Range 19 to 40 min, default 31. Change it in steps of one, watching P311. A value that is too low shows as a high return temperature. Takes effect at the next scheduled run.

**P302 Schedules: offset 2.** Range 12 to 99 min, default 87. Raise it after checking P341. A value that is too high shows as a high return temperature. Takes effect at the next scheduled run.

**P303 Schedules: night setback 3.** Range 20 to 55 %, default 35. Raise it only together with P342. A value that is too high shows as fault F235. Takes effect after the next compressor stop.

**P304 Schedules: boost time 2.** Range 12 to 34 degrees, default 19. Lower it after checking P328. A value that is too low shows as long defrosts. Takes effect at once.

**P305 Schedules: hysteresis 2.** Range 195 to 380 s, default 260. Lower it only together with P334. A wrong value shows as short cycling. Takes effect after the next compressor stop.

**P306 Schedules: curve shift 1.** Range 30 to 45 %, default 30. Raise it in steps of one, watching P302. A wrong value shows as slow heating up. Takes effect at once.

**P307 Schedules: maximum run time 2.** Range 14 to 56 degrees, default 54. Change it only together with P307. A wrong value shows as fault F385. Takes effect after the next compressor stop.

**P308 Schedules: valve run time 4.** Range 19 to 46 degrees, default 32. Change it after checking P347. A value that is too low shows as a high return temperature. Takes effect after a restart of the controller.

**P309 Schedules: pump overrun 4.** Range 21 to 70 degrees, default 21. Raise it in steps of one, watching P337. A value that is too low shows as higher energy use. Takes effect after the next compressor stop.

**P310 Schedules: alarm delay 4.** Range 5 to 7 K, default 6. Change it only together with P333. A value that is too low shows as short cycling. Takes effect after the next compressor stop.

**P311 Schedules: minimum speed 2.** Range 2 to 13 K, default 2. Raise it after checking P313. A value that is too high shows as noise at night. Takes effect after the next compressor stop.

**P312 Schedules: minimum run time 1.** Range 20 to 57 degrees, default 29. Change it only together with P332. A value that is too high shows as higher energy use. Takes effect after the next compressor stop.

**P313 Schedules: limit 1.** Range 1 to 10 K, default 3. Raise it after checking P329. A value that is too high shows as short cycling. Takes effect at the next scheduled run.

**P314 Schedules: night setback 3.** Range 120 to 430 s, default 285. Change it after checking P333. A wrong value shows as long defrosts. Takes effect after a restart of the controller.

**P315 Schedules: ramp 1.** Range 22 to 61 degrees, default 61. Raise it only together with P347. A wrong value shows as a high return temperature. Takes effect after a restart of the controller.

**P316 Schedules: ramp 3.** Range 2 to 7 K, default 4. Change it in steps of one, watching P343. A value that is too low shows as short cycling. Takes effect at the next scheduled run.

**P317 Schedules: priority 4.** Range 180 to 265 s, default 250. Change it after checking P310. A value that is too high shows as a high return temperature. Takes effect at once.

**P319 Schedules: maximum speed 2.** Range 10 to 20 %, default 10. Raise it in steps of one, watching P314. A value that is too high shows as higher energy use. Takes effect after the next compressor stop.

**P320 Schedules: maximum run time 3.** Range 35 to 100 %, default 95. Raise it in steps of one, watching P304. A value that is too high shows as long defrosts. Takes effect after a restart of the controller.

**P321 Schedules: test interval 3.** Range 23 to 91 min, default 49. Lower it after checking P346. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P322 Schedules: minimum run time 2.** Range 145 to 390 s, default 200. Raise it in steps of one, watching P322. A wrong value shows as long defrosts. Takes effect at once.

**P323 Schedules: curve slope 3.** Range 5 to 11 K, default 6. Raise it after checking P304. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P324 Schedules: valve run time 4.** Range 26 to 31 degrees, default 26. Raise it in steps of one, watching P334. A value that is too high shows as slow heating up. Takes effect after a restart of the controller.

**P325 Schedules: release temperature 4.** Range 17 to 35 degrees, default 19. Lower it in steps of one, watching P302. A value that is too low shows as slow heating up. Takes effect at once.

**P326 Schedules: valve run time 1.** Range 12 to 14 h, default 13. Change it only together with P305. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

**P327 Schedules: test interval 1.** Range 7 to 26 h, default 7. Change it after checking P338. A value that is too high shows as long defrosts. Takes effect at once.

**P328 Schedules: ramp 3.** Range 34 to 89 min, default 36. Change it after checking P348. A value that is too low shows as fault F250. Takes effect at the next scheduled run.

**P329 Schedules: pump overrun 2.** Range 18 to 72 min, default 69. Raise it after checking P344. A value that is too low shows as a high return temperature. Takes effect at once.

**P330 Schedules: alarm delay 3.** Range 7 to 16 degrees, default 16. Raise it only together with P346. A value that is too low shows as a high return temperature. Takes effect after the next compressor stop.

**P331 Schedules: valve run time 3.** Range 4 to 14 K, default 10. Change it in steps of one, watching P309. A wrong value shows as higher energy use. Takes effect after a restart of the controller.

**P332 Schedules: pump overrun 4.** Range 75 to 600 s, default 410. Lower it after checking P345. A value that is too high shows as noise at night. Takes effect at the next scheduled run.

**P333 Schedules: ramp 3.** Range 33 to 119 min, default 48. Raise it in steps of one, watching P314. A value that is too high shows as higher energy use. Takes effect after the next compressor stop.

**P334 Schedules: curve slope 4.** Range 19 to 27 h, default 26. Change it in steps of one, watching P302. A value that is too low shows as noise at night. Takes effect after the next compressor stop.

**P335 Schedules: night setback 2.** Range 17 to 66 degrees, default 23. Lower it after checking P308. A value that is too low shows as fault F282. Takes effect after a restart of the controller.

**P336 Schedules: curve shift 4.** Range 45 to 75 s, default 55. Lower it in steps of one, watching P347. A value that is too low shows as a high return temperature. Takes effect at once.

**P337 Schedules: curve shift 1.** Range 3 to 55 h, default 51. Change it in steps of one, watching P312. A value that is too low shows as noise at night. Takes effect after the next compressor stop.

**P338 Schedules: curve shift 1.** Range 19 to 54 h, default 36. Raise it after checking P312. A value that is too high shows as slow heating up. Takes effect after the next compressor stop.

**P339 Schedules: offset 1.** Range 3 to 15 K, default 8. Lower it only together with P309. A wrong value shows as a high return temperature. Takes effect at once.

**P340 Schedules: maximum speed 1.** Range 6 to 58 h, default 31. Lower it in steps of one, watching P341. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P341 Schedules: test interval 1.** Range 13 to 55 degrees, default 47. Lower it in steps of one, watching P327. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P342 Schedules: valve run time 3.** Range 150 to 320 s, default 235. Raise it in steps of one, watching P303. A value that is too high shows as long defrosts. Takes effect after a restart of the controller.

**P343 Schedules: boost time 4.** Range 27 to 119 min, default 92. Lower it in steps of one, watching P322. A wrong value shows as long defrosts. Takes effect after a restart of the controller.

**P344 Schedules: sensor correction 4.** Range 20 to 40 h, default 25. Change it after checking P314. A wrong value shows as short cycling. Takes effect at the next scheduled run.

**P345 Schedules: sensor correction 2.** Range 135 to 220 s, default 135. Lower it only together with P330. A value that is too low shows as noise at night. Takes effect at the next scheduled run.

**P346 Schedules: valve run time 2.** Range 23 to 47 h, default 36. Lower it after checking P339. A value that is too low shows as fault F335. Takes effect at the next scheduled run.

**P347 Schedules: curve slope 2.** Range 25 to 98 min, default 73. Change it in steps of one, watching P308. A value that is too low shows as short cycling. Takes effect after a restart of the controller.

**P348 Schedules: switch-over temperature 2.** Range 16 to 48 min, default 24. Raise it in steps of one, watching P347. A value that is too low shows as slow heating up. Takes effect after a restart of the controller.

**P349 Schedules: restart delay 2.** Range 15 to 100 %, default 25. Change it only together with P340. A wrong value shows as fault F183. Takes effect at the next scheduled run.

## Group 4: Hydraulics and pumps

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P400 | Hydraulics and pumps: ramp 1 | 11 to 48 | 28 | min | U |
| P401 | Hydraulics and pumps: alarm delay 2 | 6 to 57 | 45 | degrees | I |
| P402 | Hydraulics and pumps: boost time 2 | 24 to 63 | 60 | h | I |
| P403 | Hydraulics and pumps: frost limit 3 | 190 to 360 | 270 | s | S |
| P404 | Hydraulics and pumps: limit 2 | 34 to 48 | 36 | min | S |
| P405 | Hydraulics and pumps: pump overrun 2 | 50 to 420 | 65 | s | I |
| P406 | Hydraulics and pumps: target temperature 2 | 30 to 85 | 85 | s | S |
| P407 | Hydraulics and pumps: hysteresis 1 | 1 to 13 | 2 | h | S |
| P408 | Hydraulics and pumps: maximum run time 2 | 4 to 22 | 9 | h | U |
| P409 | Hydraulics and pumps: curve shift 4 | 40 to 50 | 40 | % | S |
| P410 | Hydraulics and pumps: target temperature 1 | 25 to 80 | 75 | % | I |
| P411 | Hydraulics and pumps: ramp 2 | 35 to 80 | 60 | % | I |
| P412 | Hydraulics and pumps: target temperature 2 | 17 to 52 | 51 | h | I |
| P413 | Hydraulics and pumps: alarm delay 1 | 5 to 8 | 6 | K | I |
| P414 | Hydraulics and pumps: curve shift 3 | 15 to 70 | 45 | % | S |
| P415 | Hydraulics and pumps: night setback 1 | 2 to 10 | 8 | K | S |
| P416 | Hydraulics and pumps: restart delay 2 | 15 to 48 | 47 | degrees | I |
| P417 | Hydraulics and pumps: sensor correction 1 | 10 to 45 | 25 | % | U |
| P418 | Hydraulics and pumps: valve run time 3 | 15 to 67 | 59 | h | I |
| P419 | Hydraulics and pumps: pump overrun 2 | 9 to 53 | 21 | h | U |
| P420 | Hydraulics and pumps: restart delay 4 | 10 to 70 | 50 | % | I |
| P421 | Hydraulics and pumps: maximum run time 1 | 5 to 57 | 50 | h | I |
| P422 | Hydraulics and pumps: hysteresis 2 | 20 to 85 | 20 | % | I |
| P423 | Hydraulics and pumps: frost limit 3 | 5 to 70 | 13 | degrees | S |
| P424 | Hydraulics and pumps: maximum speed 3 | 22 to 59 | 54 | h | I |
| P425 | Hydraulics and pumps: minimum run time 4 | 25 to 75 | 60 | % | I |
| P426 | Hydraulics and pumps: maximum run time 3 | 15 to 40 | 40 | % | S |
| P427 | Hydraulics and pumps: alarm delay 2 | 7 to 50 | 39 | h | U |
| P428 | Hydraulics and pumps: pump overrun 4 | 5 to 68 | 61 | h | I |
| P429 | Hydraulics and pumps: priority 1 | 4 to 13 | 4 | K | I |
| P430 | Hydraulics and pumps: restart delay 3 | 15 to 75 | 75 | % | U |
| P431 | Hydraulics and pumps: limit 2 | 18 to 53 | 24 | degrees | I |
| P432 | Hydraulics and pumps: hysteresis 3 | 28 to 92 | 48 | min | U |
| P433 | Hydraulics and pumps: limit 3 | 25 to 63 | 44 | degrees | S |
| P434 | Hydraulics and pumps: test interval 1 | 14 to 40 | 37 | min | I |
| P435 | Hydraulics and pumps: sensor correction 1 | 40 to 90 | 80 | % | I |
| P436 | Hydraulics and pumps: release temperature 4 | 7 to 52 | 50 | min | U |
| P437 | Hydraulics and pumps: boost time 4 | 3 to 15 | 4 | K | U |
| P438 | Hydraulics and pumps: curve shift 3 | 125 to 450 | 400 | s | I |
| P439 | Hydraulics and pumps: valve run time 4 | 30 to 100 | 100 | % | I |
| P440 | Hydraulics and pumps: test interval 1 | 190 to 495 | 270 | s | U |
| P441 | Hydraulics and pumps: release temperature 2 | 165 to 590 | 165 | s | S |
| P442 | Hydraulics and pumps: maximum speed 1 | 140 to 290 | 270 | s | U |
| P443 | Hydraulics and pumps: target temperature 3 | 5 to 11 | 5 | K | U |
| P444 | Hydraulics and pumps: priority 4 | 25 to 60 | 55 | % | S |
| P445 | Hydraulics and pumps: night setback 1 | 24 to 31 | 24 | degrees | U |
| P446 | Hydraulics and pumps: switch-over temperature 4 | 20 to 27 | 22 | degrees | I |
| P447 | Hydraulics and pumps: release temperature 3 | 5 to 7 | 7 | K | S |
| P448 | Hydraulics and pumps: switch-over temperature 1 | 24 to 56 | 31 | h | U |
| P449 | Hydraulics and pumps: curve shift 2 | 6 to 49 | 8 | degrees | I |
| P450 | Hydraulics and pumps: priority 1 | 115 to 200 | 195 | s | I |
| P451 | Hydraulics and pumps: offset 2 | 10 to 20 | 15 | % | I |
| P452 | Hydraulics and pumps: alarm delay 1 | 40 to 350 | 175 | s | I |
| P453 | Hydraulics and pumps: switch-over temperature 4 | 40 to 420 | 415 | s | I |
| P454 | Hydraulics and pumps: target temperature 4 | 4 to 53 | 21 | h | I |
| P455 | Hydraulics and pumps: ramp 3 | 15 to 40 | 15 | % | I |
| P456 | Hydraulics and pumps: sensor correction 2 | 35 to 240 | 75 | s | I |
| P457 | Hydraulics and pumps: valve run time 4 | 4 to 14 | 14 | K | I |
| P458 | Hydraulics and pumps: priority 3 | 15 to 75 | 70 | % | I |
| P459 | Hydraulics and pumps: minimum speed 3 | 20 to 90 | 60 | % | I |

### Group 4 in detail

**P400 Hydraulics and pumps: ramp 1.** Range 11 to 48 min, default 28. Lower it in steps of one, watching P430. A value that is too high shows as higher energy use. Takes effect after a restart of the controller.

**P401 Hydraulics and pumps: alarm delay 2.** Range 6 to 57 degrees, default 45. Change it only together with P436. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P402 Hydraulics and pumps: boost time 2.** Range 24 to 63 h, default 60. Change it after checking P402. A value that is too high shows as slow heating up. Takes effect after a restart of the controller.

**P403 Hydraulics and pumps: frost limit 3.** Range 190 to 360 s, default 270. Raise it only together with P403. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P404 Hydraulics and pumps: limit 2.** Range 34 to 48 min, default 36. Raise it in steps of one, watching P431. A value that is too high shows as a high return temperature. Takes effect at the next scheduled run.

**P405 Hydraulics and pumps: pump overrun 2.** Range 50 to 420 s, default 65. Lower it after checking P424. A value that is too low shows as noise at night. Takes effect after a restart of the controller.

**P406 Hydraulics and pumps: target temperature 2.** Range 30 to 85 s, default 85. Change it in steps of one, watching P448. A value that is too low shows as higher energy use. Takes effect after the next compressor stop.

**P407 Hydraulics and pumps: hysteresis 1.** Range 1 to 13 h, default 2. Raise it only together with P401. A value that is too high shows as fault F365. Takes effect at the next scheduled run.

**P408 Hydraulics and pumps: maximum run time 2.** Range 4 to 22 h, default 9. Change it only together with P450. A wrong value shows as higher energy use. Takes effect after a restart of the controller.

**P409 Hydraulics and pumps: curve shift 4.** Range 40 to 50 %, default 40. Lower it in steps of one, watching P423. A value that is too high shows as a high return temperature. Takes effect at once.

**P410 Hydraulics and pumps: target temperature 1.** Range 25 to 80 %, default 75. Change it after checking P450. A wrong value shows as noise at night. Takes effect after the next compressor stop.

**P411 Hydraulics and pumps: ramp 2.** Range 35 to 80 %, default 60. Raise it in steps of one, watching P450. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P412 Hydraulics and pumps: target temperature 2.** Range 17 to 52 h, default 51. Lower it in steps of one, watching P406. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P413 Hydraulics and pumps: alarm delay 1.** Range 5 to 8 K, default 6. Lower it in steps of one, watching P436. A wrong value shows as a high return temperature. Takes effect after a restart of the controller.

**P414 Hydraulics and pumps: curve shift 3.** Range 15 to 70 %, default 45. Lower it in steps of one, watching P424. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P415 Hydraulics and pumps: night setback 1.** Range 2 to 10 K, default 8. Raise it after checking P457. A wrong value shows as slow heating up. Takes effect after the next compressor stop.

**P416 Hydraulics and pumps: restart delay 2.** Range 15 to 48 degrees, default 47. Lower it only together with P424. A wrong value shows as slow heating up. Takes effect after the next compressor stop.

**P417 Hydraulics and pumps: sensor correction 1.** Range 10 to 45 %, default 25. Lower it in steps of one, watching P416. A value that is too low shows as noise at night. Takes effect after a restart of the controller.

**P418 Hydraulics and pumps: valve run time 3.** Range 15 to 67 h, default 59. Change it in steps of one, watching P423. A value that is too high shows as a high return temperature. Takes effect at the next scheduled run.

**P419 Hydraulics and pumps: pump overrun 2.** Range 9 to 53 h, default 21. Raise it only together with P458. A value that is too low shows as short cycling. Takes effect after a restart of the controller.

**P420 Hydraulics and pumps: restart delay 4.** Range 10 to 70 %, default 50. Raise it only together with P423. A value that is too high shows as a high return temperature. Takes effect after the next compressor stop.

**P421 Hydraulics and pumps: maximum run time 1.** Range 5 to 57 h, default 50. Lower it only together with P457. A value that is too high shows as higher energy use. Takes effect after the next compressor stop.

**P422 Hydraulics and pumps: hysteresis 2.** Range 20 to 85 %, default 20. Raise it in steps of one, watching P412. A wrong value shows as higher energy use. Takes effect at once.

**P423 Hydraulics and pumps: frost limit 3.** Range 5 to 70 degrees, default 13. Change it only together with P423. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P424 Hydraulics and pumps: maximum speed 3.** Range 22 to 59 h, default 54. Lower it only together with P452. A value that is too high shows as higher energy use. Takes effect at once.

**P425 Hydraulics and pumps: minimum run time 4.** Range 25 to 75 %, default 60. Change it after checking P411. A value that is too high shows as higher energy use. Takes effect after the next compressor stop.

**P426 Hydraulics and pumps: maximum run time 3.** Range 15 to 40 %, default 40. Lower it in steps of one, watching P440. A value that is too high shows as slow heating up. Takes effect after the next compressor stop.

**P427 Hydraulics and pumps: alarm delay 2.** Range 7 to 50 h, default 39. Change it only together with P409. A wrong value shows as higher energy use. Takes effect at once.

**P428 Hydraulics and pumps: pump overrun 4.** Range 5 to 68 h, default 61. Lower it only together with P439. A value that is too low shows as short cycling. Takes effect at once.

**P429 Hydraulics and pumps: priority 1.** Range 4 to 13 K, default 4. Change it only together with P442. A value that is too high shows as short cycling. Takes effect after the next compressor stop.

**P430 Hydraulics and pumps: restart delay 3.** Range 15 to 75 %, default 75. Lower it after checking P412. A value that is too low shows as higher energy use. Takes effect after the next compressor stop.

**P431 Hydraulics and pumps: limit 2.** Range 18 to 53 degrees, default 24. Raise it after checking P425. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

**P432 Hydraulics and pumps: hysteresis 3.** Range 28 to 92 min, default 48. Lower it only together with P414. A value that is too low shows as a high return temperature. Takes effect after the next compressor stop.

**P433 Hydraulics and pumps: limit 3.** Range 25 to 63 degrees, default 44. Raise it after checking P429. A value that is too low shows as a high return temperature. Takes effect at once.

**P434 Hydraulics and pumps: test interval 1.** Range 14 to 40 min, default 37. Lower it only together with P423. A value that is too low shows as short cycling. Takes effect at once.

**P435 Hydraulics and pumps: sensor correction 1.** Range 40 to 90 %, default 80. Lower it in steps of one, watching P419. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P436 Hydraulics and pumps: release temperature 4.** Range 7 to 52 min, default 50. Raise it after checking P447. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P437 Hydraulics and pumps: boost time 4.** Range 3 to 15 K, default 4. Change it after checking P424. A value that is too high shows as fault F129. Takes effect after the next compressor stop.

**P438 Hydraulics and pumps: curve shift 3.** Range 125 to 450 s, default 400. Raise it in steps of one, watching P422. A value that is too low shows as noise at night. Takes effect after a restart of the controller.

**P439 Hydraulics and pumps: valve run time 4.** Range 30 to 100 %, default 100. Raise it only together with P439. A value that is too high shows as short cycling. Takes effect after a restart of the controller.

**P440 Hydraulics and pumps: test interval 1.** Range 190 to 495 s, default 270. Change it after checking P430. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P441 Hydraulics and pumps: release temperature 2.** Range 165 to 590 s, default 165. Raise it in steps of one, watching P437. A value that is too high shows as higher energy use. Takes effect at once.

**P442 Hydraulics and pumps: maximum speed 1.** Range 140 to 290 s, default 270. Raise it after checking P454. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P443 Hydraulics and pumps: target temperature 3.** Range 5 to 11 K, default 5. Raise it only together with P438. A value that is too low shows as fault F404. Takes effect at once.

**P444 Hydraulics and pumps: priority 4.** Range 25 to 60 %, default 55. Lower it after checking P412. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P445 Hydraulics and pumps: night setback 1.** Range 24 to 31 degrees, default 24. Lower it after checking P420. A wrong value shows as slow heating up. Takes effect at once.

**P446 Hydraulics and pumps: switch-over temperature 4.** Range 20 to 27 degrees, default 22. Lower it only together with P419. A value that is too low shows as noise at night. Takes effect at the next scheduled run.

**P447 Hydraulics and pumps: release temperature 3.** Range 5 to 7 K, default 7. Change it in steps of one, watching P414. A value that is too high shows as higher energy use. Takes effect after a restart of the controller.

**P448 Hydraulics and pumps: switch-over temperature 1.** Range 24 to 56 h, default 31. Raise it after checking P416. A value that is too high shows as short cycling. Takes effect at once.

**P449 Hydraulics and pumps: curve shift 2.** Range 6 to 49 degrees, default 8. Lower it in steps of one, watching P425. A value that is too low shows as short cycling. Takes effect at the next scheduled run.

**P450 Hydraulics and pumps: priority 1.** Range 115 to 200 s, default 195. Lower it only together with P459. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P451 Hydraulics and pumps: offset 2.** Range 10 to 20 %, default 15. Change it in steps of one, watching P450. A wrong value shows as short cycling. Takes effect at once.

**P452 Hydraulics and pumps: alarm delay 1.** Range 40 to 350 s, default 175. Lower it only together with P416. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P453 Hydraulics and pumps: switch-over temperature 4.** Range 40 to 420 s, default 415. Lower it only together with P410. A value that is too low shows as fault F384. Takes effect at the next scheduled run.

**P454 Hydraulics and pumps: target temperature 4.** Range 4 to 53 h, default 21. Raise it only together with P405. A wrong value shows as short cycling. Takes effect at once.

**P455 Hydraulics and pumps: ramp 3.** Range 15 to 40 %, default 15. Lower it after checking P458. A wrong value shows as higher energy use. Takes effect at once.

**P456 Hydraulics and pumps: sensor correction 2.** Range 35 to 240 s, default 75. Change it in steps of one, watching P429. A value that is too low shows as a high return temperature. Takes effect at the next scheduled run.

**P457 Hydraulics and pumps: valve run time 4.** Range 4 to 14 K, default 14. Change it in steps of one, watching P456. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P458 Hydraulics and pumps: priority 3.** Range 15 to 75 %, default 70. Change it in steps of one, watching P413. A value that is too low shows as short cycling. Takes effect after a restart of the controller.

**P459 Hydraulics and pumps: minimum speed 3.** Range 20 to 90 %, default 60. Change it in steps of one, watching P435. A value that is too low shows as noise at night. Takes effect after a restart of the controller.

## Group 5: Cascade

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P500 | Cascade: frost limit 2 | 9 to 67 | 65 | h | I |
| P501 | Cascade: target temperature 4 | 20 to 35 | 20 | % | U |
| P502 | Cascade: restart delay 3 | 37 to 46 | 44 | min | I |
| P503 | Cascade: maximum run time 2 | 3 to 6 | 5 | K | I |
| P504 | Cascade: curve slope 4 | 9 to 52 | 35 | min | I |
| P505 | Cascade: switch-over temperature 3 | 2 to 8 | 7 | K | S |
| P506 | Cascade: minimum speed 3 | 30 to 85 | 55 | % | S |
| P507 | Cascade: minimum run time 1 | 10 to 22 | 22 | degrees | I |
| P508 | Cascade: restart delay 2 | 1 to 5 | 2 | K | I |
| P509 | Cascade: sensor correction 4 | 7 to 76 | 55 | min | I |
| P510 | Cascade: minimum run time 1 | 4 to 69 | 48 | h | U |
| P511 | Cascade: offset 1 | 35 to 90 | 35 | % | I |
| P512 | Cascade: delay after start 2 | 35 to 50 | 50 | % | I |
| P513 | Cascade: night setback 2 | 21 to 51 | 51 | degrees | I |
| P514 | Cascade: offset 1 | 26 to 32 | 28 | degrees | I |
| P515 | Cascade: valve run time 2 | 24 to 43 | 32 | degrees | S |
| P516 | Cascade: switch-over temperature 1 | 20 to 45 | 30 | % | S |
| P517 | Cascade: offset 2 | 110 to 285 | 195 | s | S |
| P518 | Cascade: priority 4 | 60 to 70 | 60 | s | I |
| P519 | Cascade: alarm delay 4 | 40 to 70 | 65 | % | I |
| P520 | Cascade: restart delay 3 | 23 to 77 | 36 | min | S |
| P521 | Cascade: frost limit 1 | 5 to 8 | 5 | K | U |
| P522 | Cascade: priority 4 | 55 to 140 | 65 | s | S |
| P523 | Cascade: limit 3 | 10 to 100 | 20 | % | I |
| P524 | Cascade: offset 4 | 105 to 135 | 120 | s | I |
| P525 | Cascade: minimum run time 1 | 15 to 50 | 30 | % | I |
| P526 | Cascade: sensor correction 1 | 21 to 29 | 26 | degrees | I |
| P527 | Cascade: valve run time 1 | 120 to 240 | 160 | s | I |
| P528 | Cascade: curve shift 3 | 20 to 47 | 29 | degrees | I |
| P529 | Cascade: alarm delay 4 | 20 to 30 | 20 | % | U |
| P530 | Cascade: test interval 3 | 7 to 85 | 28 | min | I |
| P531 | Cascade: night setback 1 | 35 to 95 | 95 | % | I |
| P532 | Cascade: valve run time 2 | 15 to 57 | 51 | degrees | I |
| P533 | Cascade: delay after start 2 | 19 to 107 | 96 | min | I |
| P534 | Cascade: ramp 1 | 20 to 50 | 40 | % | S |
| P535 | Cascade: minimum run time 1 | 6 to 53 | 11 | min | I |
| P536 | Cascade: sensor correction 3 | 125 to 470 | 370 | s | U |
| P537 | Cascade: pump overrun 1 | 40 to 50 | 40 | % | S |
| P538 | Cascade: limit 3 | 39 to 90 | 41 | min | U |
| P539 | Cascade: curve slope 2 | 2 to 9 | 5 | K | U |

### Group 5 in detail

**P500 Cascade: frost limit 2.** Range 9 to 67 h, default 65. Change it after checking P529. A value that is too low shows as noise at night. Takes effect at once.

**P501 Cascade: target temperature 4.** Range 20 to 35 %, default 20. Lower it in steps of one, watching P521. A value that is too low shows as higher energy use. Takes effect after a restart of the controller.

**P502 Cascade: restart delay 3.** Range 37 to 46 min, default 44. Change it in steps of one, watching P508. A wrong value shows as long defrosts. Takes effect after a restart of the controller.

**P503 Cascade: maximum run time 2.** Range 3 to 6 K, default 5. Change it after checking P508. A value that is too low shows as fault F285. Takes effect after the next compressor stop.

**P504 Cascade: curve slope 4.** Range 9 to 52 min, default 35. Change it after checking P503. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P505 Cascade: switch-over temperature 3.** Range 2 to 8 K, default 7. Lower it after checking P529. A value that is too low shows as slow heating up. Takes effect after a restart of the controller.

**P506 Cascade: minimum speed 3.** Range 30 to 85 %, default 55. Change it in steps of one, watching P528. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P507 Cascade: minimum run time 1.** Range 10 to 22 degrees, default 22. Raise it only together with P510. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

**P508 Cascade: restart delay 2.** Range 1 to 5 K, default 2. Raise it after checking P508. A value that is too low shows as noise at night. Takes effect after a restart of the controller.

**P509 Cascade: sensor correction 4.** Range 7 to 76 min, default 55. Change it in steps of one, watching P522. A value that is too high shows as higher energy use. Takes effect after a restart of the controller.

**P510 Cascade: minimum run time 1.** Range 4 to 69 h, default 48. Change it after checking P523. A value that is too high shows as short cycling. Takes effect at once.

**P511 Cascade: offset 1.** Range 35 to 90 %, default 35. Lower it in steps of one, watching P513. A value that is too low shows as short cycling. Takes effect after a restart of the controller.

**P512 Cascade: delay after start 2.** Range 35 to 50 %, default 50. Lower it in steps of one, watching P538. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P513 Cascade: night setback 2.** Range 21 to 51 degrees, default 51. Raise it after checking P503. A value that is too low shows as short cycling. Takes effect at once.

**P514 Cascade: offset 1.** Range 26 to 32 degrees, default 28. Lower it only together with P537. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P515 Cascade: valve run time 2.** Range 24 to 43 degrees, default 32. Lower it only together with P531. A value that is too low shows as a high return temperature. Takes effect at once.

**P516 Cascade: switch-over temperature 1.** Range 20 to 45 %, default 30. Change it in steps of one, watching P521. A value that is too high shows as slow heating up. Takes effect at the next scheduled run.

**P517 Cascade: offset 2.** Range 110 to 285 s, default 195. Lower it in steps of one, watching P533. A value that is too high shows as long defrosts. Takes effect at once.

**P518 Cascade: priority 4.** Range 60 to 70 s, default 60. Lower it only together with P504. A value that is too high shows as slow heating up. Takes effect after the next compressor stop.

**P519 Cascade: alarm delay 4.** Range 40 to 70 %, default 65. Raise it only together with P500. A wrong value shows as long defrosts. Takes effect after a restart of the controller.

**P520 Cascade: restart delay 3.** Range 23 to 77 min, default 36. Change it in steps of one, watching P538. A value that is too low shows as short cycling. Takes effect at once.

**P521 Cascade: frost limit 1.** Range 5 to 8 K, default 5. Lower it only together with P530. A value that is too high shows as fault F107. Takes effect at the next scheduled run.

**P522 Cascade: priority 4.** Range 55 to 140 s, default 65. Raise it after checking P539. A value that is too high shows as long defrosts. Takes effect at once.

**P523 Cascade: limit 3.** Range 10 to 100 %, default 20. Change it only together with P513. A value that is too high shows as noise at night. Takes effect at once.

**P524 Cascade: offset 4.** Range 105 to 135 s, default 120. Change it only together with P504. A value that is too low shows as short cycling. Takes effect at once.

**P525 Cascade: minimum run time 1.** Range 15 to 50 %, default 30. Lower it only together with P533. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P526 Cascade: sensor correction 1.** Range 21 to 29 degrees, default 26. Change it in steps of one, watching P508. A value that is too low shows as noise at night. Takes effect after a restart of the controller.

**P527 Cascade: valve run time 1.** Range 120 to 240 s, default 160. Change it after checking P539. A wrong value shows as a high return temperature. Takes effect at once.

**P528 Cascade: curve shift 3.** Range 20 to 47 degrees, default 29. Lower it after checking P534. A wrong value shows as fault F103. Takes effect at the next scheduled run.

**P529 Cascade: alarm delay 4.** Range 20 to 30 %, default 20. Raise it after checking P518. A value that is too high shows as short cycling. Takes effect at once.

**P530 Cascade: test interval 3.** Range 7 to 85 min, default 28. Raise it only together with P500. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P531 Cascade: night setback 1.** Range 35 to 95 %, default 95. Lower it only together with P524. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P532 Cascade: valve run time 2.** Range 15 to 57 degrees, default 51. Change it only together with P506. A value that is too high shows as a high return temperature. Takes effect after the next compressor stop.

**P533 Cascade: delay after start 2.** Range 19 to 107 min, default 96. Change it only together with P534. A value that is too high shows as fault F371. Takes effect after a restart of the controller.

**P534 Cascade: ramp 1.** Range 20 to 50 %, default 40. Change it only together with P521. A wrong value shows as noise at night. Takes effect after the next compressor stop.

**P535 Cascade: minimum run time 1.** Range 6 to 53 min, default 11. Raise it only together with P525. A value that is too high shows as slow heating up. Takes effect after a restart of the controller.

**P536 Cascade: sensor correction 3.** Range 125 to 470 s, default 370. Lower it after checking P533. A value that is too high shows as fault F273. Takes effect at once.

**P537 Cascade: pump overrun 1.** Range 40 to 50 %, default 40. Raise it only together with P524. A value that is too high shows as fault F304. Takes effect at once.

**P538 Cascade: limit 3.** Range 39 to 90 min, default 41. Lower it after checking P502. A value that is too high shows as noise at night. Takes effect at the next scheduled run.

**P539 Cascade: curve slope 2.** Range 2 to 9 K, default 5. Raise it only together with P517. A wrong value shows as long defrosts. Takes effect after the next compressor stop.

## Group 6: Inputs and outputs

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P600 | Inputs and outputs: curve shift 4 | 8 to 57 | 56 | min | U |
| P601 | Inputs and outputs: boost time 2 | 35 to 55 | 50 | % | U |
| P602 | Inputs and outputs: offset 4 | 4 to 7 | 6 | K | U |
| P603 | Inputs and outputs: maximum speed 4 | 39 to 48 | 48 | min | I |
| P604 | Inputs and outputs: curve shift 3 | 15 to 25 | 25 | % | U |
| P605 | Inputs and outputs: maximum run time 4 | 40 to 100 | 50 | % | S |
| P606 | Inputs and outputs: boost time 3 | 23 to 69 | 47 | h | I |
| P607 | Inputs and outputs: hysteresis 4 | 50 to 420 | 95 | s | I |
| P608 | Inputs and outputs: pump overrun 2 | 15 to 50 | 25 | % | U |
| P609 | Inputs and outputs: hysteresis 2 | 9 to 65 | 16 | degrees | S |
| P610 | Inputs and outputs: frost limit 2 | 100 to 515 | 430 | s | I |
| P611 | Inputs and outputs: curve slope 1 | 40 to 55 | 40 | % | I |
| P612 | Inputs and outputs: hysteresis 2 | 16 to 22 | 20 | min | S |
| P613 | Inputs and outputs: offset 2 | 7 to 89 | 51 | min | I |
| P614 | Inputs and outputs: pump overrun 4 | 40 to 100 | 50 | % | I |
| P615 | Inputs and outputs: frost limit 1 | 40 to 42 | 41 | min | I |
| P616 | Inputs and outputs: test interval 3 | 15 to 39 | 19 | h | I |
| P617 | Inputs and outputs: release temperature 1 | 135 to 455 | 410 | s | I |
| P618 | Inputs and outputs: sensor correction 4 | 20 to 45 | 20 | % | I |
| P619 | Inputs and outputs: offset 2 | 65 to 350 | 125 | s | U |
| P620 | Inputs and outputs: maximum speed 2 | 6 to 8 | 6 | h | I |
| P621 | Inputs and outputs: curve slope 2 | 5 to 13 | 9 | K | I |
| P622 | Inputs and outputs: test interval 3 | 10 to 67 | 54 | degrees | I |
| P623 | Inputs and outputs: target temperature 4 | 5 to 15 | 11 | K | U |
| P624 | Inputs and outputs: night setback 3 | 10 to 19 | 13 | h | I |
| P625 | Inputs and outputs: target temperature 1 | 7 to 25 | 21 | h | I |
| P626 | Inputs and outputs: night setback 3 | 20 to 70 | 40 | % | I |
| P627 | Inputs and outputs: offset 4 | 10 to 64 | 10 | h | S |
| P628 | Inputs and outputs: offset 1 | 15 to 85 | 60 | % | I |
| P629 | Inputs and outputs: release temperature 4 | 165 to 425 | 415 | s | S |
| P630 | Inputs and outputs: valve run time 3 | 6 to 64 | 28 | degrees | I |
| P631 | Inputs and outputs: delay after start 4 | 3 to 7 | 3 | K | I |
| P632 | Inputs and outputs: minimum speed 1 | 6 to 14 | 11 | h | I |
| P633 | Inputs and outputs: frost limit 4 | 39 to 97 | 74 | min | I |
| P634 | Inputs and outputs: restart delay 1 | 20 to 65 | 60 | % | I |
| P635 | Inputs and outputs: offset 1 | 8 to 52 | 51 | h | I |
| P636 | Inputs and outputs: pump overrun 4 | 25 to 50 | 35 | % | I |
| P637 | Inputs and outputs: switch-over temperature 4 | 20 to 85 | 75 | % | S |
| P638 | Inputs and outputs: frost limit 2 | 25 to 42 | 29 | degrees | I |
| P639 | Inputs and outputs: limit 2 | 9 to 35 | 12 | h | S |
| P640 | Inputs and outputs: hysteresis 3 | 15 to 85 | 85 | % | U |
| P641 | Inputs and outputs: sensor correction 2 | 40 to 95 | 90 | % | I |
| P642 | Inputs and outputs: curve slope 3 | 185 to 260 | 210 | s | S |
| P643 | Inputs and outputs: offset 1 | 60 to 365 | 295 | s | I |
| P644 | Inputs and outputs: offset 1 | 90 to 130 | 90 | s | I |
| P645 | Inputs and outputs: limit 3 | 10 to 13 | 12 | min | I |
| P646 | Inputs and outputs: pump overrun 1 | 1 to 11 | 3 | K | I |
| P647 | Inputs and outputs: offset 3 | 3 to 10 | 8 | K | S |
| P648 | Inputs and outputs: target temperature 4 | 1 to 11 | 4 | K | S |
| P649 | Inputs and outputs: offset 3 | 35 to 55 | 55 | % | I |

### Group 6 in detail

**P600 Inputs and outputs: curve shift 4.** Range 8 to 57 min, default 56. Change it only together with P606. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P601 Inputs and outputs: boost time 2.** Range 35 to 55 %, default 50. Lower it in steps of one, watching P611. A value that is too low shows as long defrosts. Takes effect at once.

**P602 Inputs and outputs: offset 4.** Range 4 to 7 K, default 6. Lower it in steps of one, watching P638. A wrong value shows as higher energy use. Takes effect after the next compressor stop.

**P603 Inputs and outputs: maximum speed 4.** Range 39 to 48 min, default 48. Lower it after checking P646. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P604 Inputs and outputs: curve shift 3.** Range 15 to 25 %, default 25. Raise it in steps of one, watching P614. A value that is too high shows as noise at night. Takes effect after the next compressor stop.

**P605 Inputs and outputs: maximum run time 4.** Range 40 to 100 %, default 50. Change it only together with P618. A value that is too high shows as noise at night. Takes effect after the next compressor stop.

**P606 Inputs and outputs: boost time 3.** Range 23 to 69 h, default 47. Change it after checking P607. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P607 Inputs and outputs: hysteresis 4.** Range 50 to 420 s, default 95. Lower it in steps of one, watching P603. A value that is too low shows as fault F332. Takes effect at once.

**P608 Inputs and outputs: pump overrun 2.** Range 15 to 50 %, default 25. Raise it in steps of one, watching P632. A value that is too high shows as higher energy use. Takes effect at once.

**P609 Inputs and outputs: hysteresis 2.** Range 9 to 65 degrees, default 16. Change it after checking P633. A value that is too high shows as slow heating up. Takes effect at the next scheduled run.

**P610 Inputs and outputs: frost limit 2.** Range 100 to 515 s, default 430. Change it only together with P648. A value that is too low shows as a high return temperature. Takes effect at the next scheduled run.

**P611 Inputs and outputs: curve slope 1.** Range 40 to 55 %, default 40. Raise it after checking P628. A value that is too high shows as fault F229. Takes effect after a restart of the controller.

**P612 Inputs and outputs: hysteresis 2.** Range 16 to 22 min, default 20. Change it only together with P625. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P613 Inputs and outputs: offset 2.** Range 7 to 89 min, default 51. Lower it only together with P632. A value that is too low shows as fault F354. Takes effect after the next compressor stop.

**P614 Inputs and outputs: pump overrun 4.** Range 40 to 100 %, default 50. Lower it only together with P646. A wrong value shows as short cycling. Takes effect after the next compressor stop.

**P615 Inputs and outputs: frost limit 1.** Range 40 to 42 min, default 41. Lower it after checking P620. A value that is too low shows as fault F202. Takes effect after a restart of the controller.

**P616 Inputs and outputs: test interval 3.** Range 15 to 39 h, default 19. Change it after checking P610. A value that is too high shows as short cycling. Takes effect at the next scheduled run.

**P617 Inputs and outputs: release temperature 1.** Range 135 to 455 s, default 410. Lower it only together with P613. A wrong value shows as fault F377. Takes effect at once.

**P618 Inputs and outputs: sensor correction 4.** Range 20 to 45 %, default 20. Lower it in steps of one, watching P632. A wrong value shows as higher energy use. Takes effect at once.

**P619 Inputs and outputs: offset 2.** Range 65 to 350 s, default 125. Change it only together with P642. A value that is too low shows as long defrosts. Takes effect after a restart of the controller.

**P620 Inputs and outputs: maximum speed 2.** Range 6 to 8 h, default 6. Lower it in steps of one, watching P610. A value that is too low shows as long defrosts. Takes effect at the next scheduled run.

**P621 Inputs and outputs: curve slope 2.** Range 5 to 13 K, default 9. Raise it in steps of one, watching P649. A wrong value shows as long defrosts. Takes effect at the next scheduled run.

**P622 Inputs and outputs: test interval 3.** Range 10 to 67 degrees, default 54. Lower it only together with P606. A value that is too high shows as fault F156. Takes effect at the next scheduled run.

**P623 Inputs and outputs: target temperature 4.** Range 5 to 15 K, default 11. Lower it after checking P610. A wrong value shows as a high return temperature. Takes effect after the next compressor stop.

**P624 Inputs and outputs: night setback 3.** Range 10 to 19 h, default 13. Raise it after checking P602. A wrong value shows as short cycling. Takes effect after a restart of the controller.

**P625 Inputs and outputs: target temperature 1.** Range 7 to 25 h, default 21. Raise it after checking P626. A value that is too low shows as slow heating up. Takes effect at the next scheduled run.

**P626 Inputs and outputs: night setback 3.** Range 20 to 70 %, default 40. Change it only together with P629. A wrong value shows as short cycling. Takes effect after the next compressor stop.

**P627 Inputs and outputs: offset 4.** Range 10 to 64 h, default 10. Lower it only together with P609. A wrong value shows as slow heating up. Takes effect at once.

**P628 Inputs and outputs: offset 1.** Range 15 to 85 %, default 60. Raise it in steps of one, watching P625. A wrong value shows as a high return temperature. Takes effect after the next compressor stop.

**P629 Inputs and outputs: release temperature 4.** Range 165 to 425 s, default 415. Change it only together with P606. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P630 Inputs and outputs: valve run time 3.** Range 6 to 64 degrees, default 28. Lower it after checking P641. A value that is too high shows as long defrosts. Takes effect at once.

**P631 Inputs and outputs: delay after start 4.** Range 3 to 7 K, default 3. Raise it after checking P611. A value that is too high shows as short cycling. Takes effect at the next scheduled run.

**P632 Inputs and outputs: minimum speed 1.** Range 6 to 14 h, default 11. Lower it only together with P637. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P633 Inputs and outputs: frost limit 4.** Range 39 to 97 min, default 74. Raise it after checking P617. A value that is too low shows as noise at night. Takes effect at the next scheduled run.

**P634 Inputs and outputs: restart delay 1.** Range 20 to 65 %, default 60. Lower it only together with P619. A wrong value shows as a high return temperature. Takes effect at the next scheduled run.

**P635 Inputs and outputs: offset 1.** Range 8 to 52 h, default 51. Raise it in steps of one, watching P628. A value that is too low shows as higher energy use. Takes effect at the next scheduled run.

**P636 Inputs and outputs: pump overrun 4.** Range 25 to 50 %, default 35. Raise it in steps of one, watching P631. A value that is too high shows as a high return temperature. Takes effect after the next compressor stop.

**P637 Inputs and outputs: switch-over temperature 4.** Range 20 to 85 %, default 75. Change it in steps of one, watching P608. A value that is too low shows as noise at night. Takes effect after a restart of the controller.

**P638 Inputs and outputs: frost limit 2.** Range 25 to 42 degrees, default 29. Raise it after checking P629. A wrong value shows as fault F305. Takes effect after a restart of the controller.

**P639 Inputs and outputs: limit 2.** Range 9 to 35 h, default 12. Raise it in steps of one, watching P635. A wrong value shows as fault F285. Takes effect at the next scheduled run.

**P640 Inputs and outputs: hysteresis 3.** Range 15 to 85 %, default 85. Lower it in steps of one, watching P605. A value that is too high shows as slow heating up. Takes effect at the next scheduled run.

**P641 Inputs and outputs: sensor correction 2.** Range 40 to 95 %, default 90. Lower it after checking P627. A value that is too low shows as noise at night. Takes effect after the next compressor stop.

**P642 Inputs and outputs: curve slope 3.** Range 185 to 260 s, default 210. Change it only together with P642. A value that is too high shows as fault F246. Takes effect at once.

**P643 Inputs and outputs: offset 1.** Range 60 to 365 s, default 295. Lower it in steps of one, watching P622. A wrong value shows as noise at night. Takes effect at once.

**P644 Inputs and outputs: offset 1.** Range 90 to 130 s, default 90. Raise it after checking P617. A value that is too high shows as a high return temperature. Takes effect after the next compressor stop.

**P645 Inputs and outputs: limit 3.** Range 10 to 13 min, default 12. Lower it after checking P641. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P646 Inputs and outputs: pump overrun 1.** Range 1 to 11 K, default 3. Change it in steps of one, watching P618. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P647 Inputs and outputs: offset 3.** Range 3 to 10 K, default 8. Change it after checking P600. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P648 Inputs and outputs: target temperature 4.** Range 1 to 11 K, default 4. Raise it after checking P647. A wrong value shows as noise at night. Takes effect at once.

**P649 Inputs and outputs: offset 3.** Range 35 to 55 %, default 55. Raise it in steps of one, watching P640. A value that is too low shows as higher energy use. Takes effect at the next scheduled run.

## Group 7: Service

| Parameter | Name | Range | Default | Unit | Access |
|---|---|---|---|---|---|
| P700 | Service: hysteresis 2 | 1 to 4 | 2 | K | I |
| P701 | Service: minimum run time 1 | 17 to 27 | 21 | h | U |
| P702 | Service: offset 4 | 8 to 45 | 15 | degrees | I |
| P703 | Service: hysteresis 1 | 20 to 60 | 35 | % | S |
| P704 | Service: minimum speed 1 | 24 to 54 | 24 | h | I |
| P705 | Service: pump overrun 3 | 1 to 32 | 7 | h | I |
| P706 | Service: restart delay 4 | 3 to 5 | 4 | K | I |
| P707 | Service: curve shift 4 | 20 to 95 | 40 | % | I |
| P708 | Service: frost limit 1 | 145 to 470 | 290 | s | I |
| P709 | Service: maximum speed 3 | 30 to 60 | 40 | % | I |
| P710 | Service: frost limit 2 | 7 to 112 | 58 | min | I |
| P711 | Service: maximum speed 4 | 23 to 54 | 32 | degrees | I |
| P712 | Service: ramp 2 | 35 to 60 | 35 | % | I |
| P713 | Service: pump overrun 2 | 155 to 335 | 305 | s | U |
| P714 | Service: boost time 1 | 25 to 59 | 45 | degrees | I |
| P715 | Service: maximum speed 3 | 4 to 14 | 4 | min | I |
| P716 | Service: test interval 1 | 35 to 65 | 40 | % | U |
| P717 | Service: alarm delay 2 | 19 to 45 | 21 | degrees | I |
| P718 | Service: release temperature 4 | 30 to 155 | 75 | s | U |
| P719 | Service: hysteresis 1 | 70 to 160 | 85 | s | S |
| P720 | Service: night setback 3 | 1 to 3 | 2 | K | I |
| P721 | Service: offset 1 | 14 to 46 | 37 | h | U |
| P722 | Service: switch-over temperature 2 | 85 to 265 | 210 | s | I |
| P723 | Service: minimum run time 1 | 16 to 66 | 23 | degrees | I |
| P724 | Service: pump overrun 3 | 18 to 53 | 43 | h | I |
| P725 | Service: ramp 2 | 35 to 85 | 55 | % | S |
| P726 | Service: minimum run time 2 | 1 to 4 | 1 | K | I |
| P727 | Service: valve run time 2 | 20 to 90 | 75 | % | I |
| P728 | Service: switch-over temperature 2 | 15 to 35 | 25 | % | I |
| P729 | Service: curve slope 3 | 7 to 15 | 9 | degrees | I |
| P730 | Service: hysteresis 4 | 175 to 500 | 245 | s | I |
| P731 | Service: pump overrun 4 | 2 to 9 | 8 | K | I |
| P732 | Service: delay after start 1 | 15 to 60 | 25 | % | I |
| P733 | Service: night setback 1 | 200 to 430 | 395 | s | U |
| P734 | Service: curve slope 4 | 23 to 37 | 28 | min | I |
| P735 | Service: offset 2 | 1 to 11 | 6 | K | I |
| P736 | Service: ramp 1 | 6 to 9 | 7 | degrees | I |
| P737 | Service: curve slope 1 | 27 to 31 | 31 | min | I |
| P738 | Service: boost time 3 | 18 to 34 | 24 | degrees | I |
| P739 | Service: switch-over temperature 2 | 30 to 50 | 50 | % | S |
| P740 | Service: sensor correction 3 | 4 to 9 | 9 | K | S |
| P741 | Service: restart delay 3 | 10 to 65 | 15 | % | I |
| P742 | Service: offset 1 | 45 to 125 | 110 | s | I |
| P743 | Service: priority 1 | 120 to 350 | 235 | s | U |
| P744 | Service: limit 3 | 125 to 420 | 340 | s | S |
| P745 | Service: release temperature 2 | 20 to 56 | 34 | degrees | I |
| P746 | Service: minimum run time 3 | 15 to 95 | 35 | % | I |
| P747 | Service: curve shift 3 | 5 to 46 | 16 | h | I |
| P748 | Service: minimum run time 1 | 40 to 85 | 50 | % | I |
| P749 | Service: sensor correction 3 | 40 to 85 | 70 | % | I |

### Group 7 in detail

**P700 Service: hysteresis 2.** Range 1 to 4 K, default 2. Raise it after checking P740. A wrong value shows as slow heating up. Takes effect at once.

**P701 Service: minimum run time 1.** Range 17 to 27 h, default 21. Raise it only together with P711. A value that is too low shows as long defrosts. Takes effect at once.

**P702 Service: offset 4.** Range 8 to 45 degrees, default 15. Lower it in steps of one, watching P724. A value that is too low shows as higher energy use. Takes effect after a restart of the controller.

**P703 Service: hysteresis 1.** Range 20 to 60 %, default 35. Lower it in steps of one, watching P711. A wrong value shows as fault F147. Takes effect at the next scheduled run.

**P704 Service: minimum speed 1.** Range 24 to 54 h, default 24. Lower it after checking P735. A wrong value shows as a high return temperature. Takes effect after a restart of the controller.

**P705 Service: pump overrun 3.** Range 1 to 32 h, default 7. Lower it only together with P727. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P706 Service: restart delay 4.** Range 3 to 5 K, default 4. Lower it only together with P722. A wrong value shows as fault F359. Takes effect at the next scheduled run.

**P707 Service: curve shift 4.** Range 20 to 95 %, default 40. Raise it after checking P737. A value that is too low shows as long defrosts. Takes effect after the next compressor stop.

**P708 Service: frost limit 1.** Range 145 to 470 s, default 290. Raise it only together with P730. A value that is too low shows as a high return temperature. Takes effect after the next compressor stop.

**P709 Service: maximum speed 3.** Range 30 to 60 %, default 40. Raise it after checking P711. A wrong value shows as noise at night. Takes effect after a restart of the controller.

**P710 Service: frost limit 2.** Range 7 to 112 min, default 58. Lower it after checking P717. A value that is too high shows as long defrosts. Takes effect after the next compressor stop.

**P711 Service: maximum speed 4.** Range 23 to 54 degrees, default 32. Lower it in steps of one, watching P748. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P712 Service: ramp 2.** Range 35 to 60 %, default 35. Lower it after checking P732. A value that is too high shows as a high return temperature. Takes effect at once.

**P713 Service: pump overrun 2.** Range 155 to 335 s, default 305. Lower it in steps of one, watching P727. A value that is too high shows as higher energy use. Takes effect at once.

**P714 Service: boost time 1.** Range 25 to 59 degrees, default 45. Lower it only together with P731. A value that is too high shows as higher energy use. Takes effect after a restart of the controller.

**P715 Service: maximum speed 3.** Range 4 to 14 min, default 4. Lower it only together with P706. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P716 Service: test interval 1.** Range 35 to 65 %, default 40. Lower it only together with P710. A wrong value shows as slow heating up. Takes effect after a restart of the controller.

**P717 Service: alarm delay 2.** Range 19 to 45 degrees, default 21. Lower it in steps of one, watching P740. A value that is too low shows as slow heating up. Takes effect after a restart of the controller.

**P718 Service: release temperature 4.** Range 30 to 155 s, default 75. Change it in steps of one, watching P713. A value that is too high shows as a high return temperature. Takes effect after a restart of the controller.

**P719 Service: hysteresis 1.** Range 70 to 160 s, default 85. Change it after checking P743. A wrong value shows as fault F388. Takes effect at the next scheduled run.

**P720 Service: night setback 3.** Range 1 to 3 K, default 2. Change it only together with P731. A wrong value shows as short cycling. Takes effect after the next compressor stop.

**P721 Service: offset 1.** Range 14 to 46 h, default 37. Change it in steps of one, watching P744. A wrong value shows as short cycling. Takes effect after the next compressor stop.

**P722 Service: switch-over temperature 2.** Range 85 to 265 s, default 210. Lower it only together with P715. A value that is too high shows as higher energy use. Takes effect at once.

**P723 Service: minimum run time 1.** Range 16 to 66 degrees, default 23. Change it in steps of one, watching P749. A wrong value shows as slow heating up. Takes effect at once.

**P724 Service: pump overrun 3.** Range 18 to 53 h, default 43. Change it in steps of one, watching P706. A wrong value shows as noise at night. Takes effect after the next compressor stop.

**P725 Service: ramp 2.** Range 35 to 85 %, default 55. Raise it after checking P735. A value that is too high shows as a high return temperature. Takes effect after the next compressor stop.

**P726 Service: minimum run time 2.** Range 1 to 4 K, default 1. Raise it in steps of one, watching P701. A value that is too low shows as higher energy use. Takes effect after the next compressor stop.

**P727 Service: valve run time 2.** Range 20 to 90 %, default 75. Lower it in steps of one, watching P716. A value that is too low shows as a high return temperature. Takes effect after a restart of the controller.

**P728 Service: switch-over temperature 2.** Range 15 to 35 %, default 25. Raise it after checking P714. A value that is too high shows as long defrosts. Takes effect at once.

**P729 Service: curve slope 3.** Range 7 to 15 degrees, default 9. Lower it in steps of one, watching P740. A wrong value shows as noise at night. Takes effect at the next scheduled run.

**P730 Service: hysteresis 4.** Range 175 to 500 s, default 245. Raise it only together with P735. A value that is too high shows as long defrosts. Takes effect at the next scheduled run.

**P731 Service: pump overrun 4.** Range 2 to 9 K, default 8. Raise it after checking P725. A wrong value shows as long defrosts. Takes effect at the next scheduled run.

**P732 Service: delay after start 1.** Range 15 to 60 %, default 25. Lower it only together with P711. A wrong value shows as short cycling. Takes effect at the next scheduled run.

**P733 Service: night setback 1.** Range 200 to 430 s, default 395. Change it in steps of one, watching P702. A value that is too low shows as fault F184. Takes effect at the next scheduled run.

**P734 Service: curve slope 4.** Range 23 to 37 min, default 28. Raise it only together with P722. A value that is too high shows as a high return temperature. Takes effect at the next scheduled run.

**P735 Service: offset 2.** Range 1 to 11 K, default 6. Lower it after checking P721. A value that is too high shows as noise at night. Takes effect after a restart of the controller.

**P736 Service: ramp 1.** Range 6 to 9 degrees, default 7. Change it in steps of one, watching P702. A wrong value shows as slow heating up. Takes effect at the next scheduled run.

**P737 Service: curve slope 1.** Range 27 to 31 min, default 31. Raise it after checking P715. A value that is too high shows as long defrosts. Takes effect after a restart of the controller.

**P738 Service: boost time 3.** Range 18 to 34 degrees, default 24. Lower it in steps of one, watching P701. A wrong value shows as fault F303. Takes effect after a restart of the controller.

**P739 Service: switch-over temperature 2.** Range 30 to 50 %, default 50. Change it only together with P731. A value that is too high shows as fault F387. Takes effect after a restart of the controller.

**P740 Service: sensor correction 3.** Range 4 to 9 K, default 9. Change it only together with P746. A value that is too low shows as higher energy use. Takes effect after the next compressor stop.

**P741 Service: restart delay 3.** Range 10 to 65 %, default 15. Lower it in steps of one, watching P721. A value that is too low shows as noise at night. Takes effect at the next scheduled run.

**P742 Service: offset 1.** Range 45 to 125 s, default 110. Raise it after checking P704. A wrong value shows as noise at night. Takes effect at once.

**P743 Service: priority 1.** Range 120 to 350 s, default 235. Change it after checking P744. A wrong value shows as higher energy use. Takes effect after the next compressor stop.

**P744 Service: limit 3.** Range 125 to 420 s, default 340. Lower it in steps of one, watching P736. A value that is too low shows as slow heating up. Takes effect after the next compressor stop.

**P745 Service: release temperature 2.** Range 20 to 56 degrees, default 34. Change it only together with P711. A value that is too high shows as higher energy use. Takes effect after the next compressor stop.

**P746 Service: minimum run time 3.** Range 15 to 95 %, default 35. Change it in steps of one, watching P703. A value that is too low shows as a high return temperature. Takes effect at once.

**P747 Service: curve shift 3.** Range 5 to 46 h, default 16. Raise it only together with P718. A value that is too low shows as noise at night. Takes effect at once.

**P748 Service: minimum run time 1.** Range 40 to 85 %, default 50. Change it only together with P740. A value that is too high shows as noise at night. Takes effect after the next compressor stop.

**P749 Service: sensor correction 3.** Range 40 to 85 %, default 70. Lower it only together with P714. A wrong value shows as a high return temperature. Takes effect after the next compressor stop.

## Notes on important parameters

**P112 and P113 (anti-legionella).** Once a week the hot water tank is heated to the P112 target and held for 30 minutes. With the default of 55 degrees the electric backup heater is not needed; above 60 degrees the backup heater finishes the program. Health rules for buildings with showers used by the public ask for at least 60 degrees: set P112 to 60 there.

**P205 (minimum off time).** Protects the compressor from short cycling. Do not set it below the default without Veltra's consent.

**P210 (defrost interval).** A shorter interval helps in freezing fog; a longer one saves energy in dry cold.

**P318 (quiet mode).** The fan speed limit during quiet hours. Each 10% less lowers the sound pressure by about 2 dB(A) and the heating capacity by about 6%.

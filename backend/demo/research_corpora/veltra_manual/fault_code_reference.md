# Veltra HX Fault Code Reference

Firmware 2.4. Faults F100 to F199 concern the refrigerant circuit, F200 to F299 the water side and defrost, F300 to F349 safety, F350 to F419 electronics and communication. A fault that "locks the unit" needs a reset; the last 50 faults are in the history (service menu 2.1).

| Code | Meaning | What the unit does | What to do |
|---|---|---|---|
| F100 | Discharge gas sensor: over-temperature | locks the unit until reset by service | check the supply and the fuses |
| F101 | Buffer sensor: limit not reached in time | resets itself | update the firmware |
| F102 | Crankcase heater: over-current | locks the unit until reset at the controller | measure the resistance against the sensor table |
| F103 | Discharge gas sensor: value outside the plausible range | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F104 | Hot water tank sensor: flow too low | locks the unit until reset at the controller | replace the part |
| F105 | Mixing valve: limit not reached in time | warning only | clean the strainer and bleed the circuit |
| F106 | Circulation pump: phase missing | resets itself after 10 minutes | clean the strainer and bleed the circuit |
| F107 | Outdoor air sensor: value outside the plausible range | locks the unit until reset at the controller | check the refrigerant circuit for leaks (certified staff only) |
| F108 | Backup heater: limit exceeded | warning only | check the setting of the related parameter |
| F109 | Bus module: pressure too low | locks the unit until reset by service | replace the part |
| F110 | Mixing valve: contact did not close | switches to backup heating | check the refrigerant circuit for leaks (certified staff only) |
| F111 | Crankcase heater: pressure too low | switches to backup heating | restart the controller; if it returns, call service |
| F112 | Low pressure transducer: limit exceeded | warning only | let the unit cool down and check the air path |
| F113 | Crankcase heater: limit exceeded | resets itself | check the refrigerant circuit for leaks (certified staff only) |
| F114 | Compressor: contact did not open | resets itself after 10 minutes | let the unit cool down and check the air path |
| F115 | Return sensor: limit exceeded | locks the unit until reset at the controller | check the plug and the cable, then replace the part |
| F116 | High pressure switch: sensor open circuit | switches to backup heating | update the firmware |
| F117 | Low pressure transducer: over-current | resets itself after 10 minutes | replace the part |
| F118 | Buffer sensor: checksum error | switches to backup heating | check the setting of the related parameter |
| F119 | Low pressure transducer: no communication | warning only | check the supply and the fuses |
| F120 | Mixing valve: flow too low | locks the unit until reset at the controller | let the unit cool down and check the air path |
| F121 | Condensate heater: checksum error | resets itself after 10 minutes | clean the strainer and bleed the circuit |
| F122 | Discharge gas sensor: flow too low | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F123 | Flow sensor: limit not reached in time | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F124 | Bus module: contact did not close | resets itself after 10 minutes | check the supply and the fuses |
| F125 | Compressor: sensor open circuit | locks the unit until reset at the controller | check the refrigerant circuit for leaks (certified staff only) |
| F126 | Suction gas sensor: limit exceeded | resets itself after 10 minutes | check the setting of the related parameter |
| F127 | Low pressure transducer: limit not reached in time | resets itself after 10 minutes | check the setting of the related parameter |
| F128 | Flow sensor: no communication | resets itself | replace the part |
| F129 | Fan 2: over-temperature | warning only | restart the controller; if it returns, call service |
| F130 | Flow sensor: contact did not close | switches to backup heating | check the refrigerant circuit for leaks (certified staff only) |
| F131 | Backup heater: sensor open circuit | resets itself | check the setting of the related parameter |
| F132 | Backup heater: contact did not open | locks the unit until reset by service | replace the part |
| F133 | Controller board: pressure too low | switches to backup heating | let the unit cool down and check the air path |
| F134 | Circulation pump: over-temperature | switches to backup heating | measure the resistance against the sensor table |
| F135 | Outdoor air sensor: contact did not close | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F136 | Inverter: flow too low | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F137 | Flow meter: checksum error | locks the unit until reset at the controller | measure the resistance against the sensor table |
| F138 | Flow sensor: configuration mismatch | resets itself | restart the controller; if it returns, call service |
| F139 | Suction gas sensor: pressure too high | switches to backup heating | let the unit cool down and check the air path |
| F140 | Circulation pump: phase missing | resets itself | check the refrigerant circuit for leaks (certified staff only) |
| F141 | Circulation pump: contact did not close | resets itself | restart the controller; if it returns, call service |
| F142 | Fan 2: sensor open circuit | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F143 | Inverter: over-current | switches to backup heating | check the refrigerant circuit for leaks (certified staff only) |
| F144 | High pressure switch: over-current | warning only | check the setting of the related parameter |
| F145 | High pressure switch: configuration mismatch | resets itself after 10 minutes | check the setting of the related parameter |
| F146 | High pressure switch: over-temperature | locks the unit until reset at the controller | check the supply and the fuses |
| F147 | High pressure switch tripped | resets itself after 10 minutes; locks the unit after 3 events in 24 hours | clean the strainer, check the flow against the minimum flow, check the fan and the heat exchanger |
| F148 | Diverter valve: no communication | resets itself after 10 minutes | check the supply and the fuses |
| F149 | Buffer sensor: value outside the plausible range | switches to backup heating | restart the controller; if it returns, call service |
| F150 | Flow meter: flow too low | warning only | let the unit cool down and check the air path |
| F151 | Bus module: sensor short circuit | resets itself after 10 minutes | restart the controller; if it returns, call service |
| F152 | Flow meter: flow too low | warning only | check the setting of the related parameter |
| F153 | Compressor: value outside the plausible range | locks the unit until reset at the controller | check the setting of the related parameter |
| F154 | Buffer sensor: pressure too high | resets itself | check the plug and the cable, then replace the part |
| F155 | Suction gas sensor: limit not reached in time | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F156 | Fan 2: contact did not close | warning only | check the plug and the cable, then replace the part |
| F157 | Bus module: no communication | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F158 | Buffer sensor: pressure too low | switches to backup heating | check the setting of the related parameter |
| F159 | Fan 1: limit exceeded | warning only | update the firmware |
| F160 | Return sensor: pressure too high | resets itself | replace the part |
| F161 | Hot water tank sensor: sensor short circuit | locks the unit until reset by service | check the setting of the related parameter |
| F162 | Suction gas sensor: phase missing | locks the unit until reset at the controller | clean the strainer and bleed the circuit |
| F163 | Compressor: over-current | warning only | measure the resistance against the sensor table |
| F164 | Low pressure transducer: phase missing | locks the unit until reset at the controller | check the plug and the cable, then replace the part |
| F165 | High pressure switch: pressure too low | locks the unit until reset at the controller | check the refrigerant circuit for leaks (certified staff only) |
| F166 | Flow meter: flow too low | locks the unit until reset at the controller | check the setting of the related parameter |
| F167 | High pressure switch: phase missing | locks the unit until reset by service | check the refrigerant circuit for leaks (certified staff only) |
| F168 | Flow meter: flow too low | warning only | clean the strainer and bleed the circuit |
| F169 | Bus module: contact did not open | resets itself | restart the controller; if it returns, call service |
| F170 | High pressure switch: pressure too high | switches to backup heating | restart the controller; if it returns, call service |
| F171 | Condensate heater: limit exceeded | switches to backup heating | measure the resistance against the sensor table |
| F172 | Buffer sensor: no communication | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F173 | High pressure switch: contact did not open | locks the unit until reset at the controller | restart the controller; if it returns, call service |
| F174 | Return sensor: over-temperature | resets itself after 10 minutes | check the refrigerant circuit for leaks (certified staff only) |
| F175 | Controller board: configuration mismatch | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F176 | Mixing valve: over-current | warning only | replace the part |
| F177 | Fan 1: contact did not open | locks the unit until reset at the controller | replace the part |
| F178 | Fan 2: pressure too low | locks the unit until reset at the controller | update the firmware |
| F179 | Fan 2: value outside the plausible range | locks the unit until reset at the controller | let the unit cool down and check the air path |
| F180 | Controller board: phase missing | resets itself | update the firmware |
| F181 | Fan 1: flow too low | locks the unit until reset by service | measure the resistance against the sensor table |
| F182 | High pressure switch: limit not reached in time | switches to backup heating | update the firmware |
| F183 | High pressure switch: limit exceeded | locks the unit until reset at the controller | measure the resistance against the sensor table |
| F184 | Backup heater: over-temperature | switches to backup heating | let the unit cool down and check the air path |
| F185 | Hot water tank sensor: over-current | resets itself | measure the resistance against the sensor table |
| F186 | Discharge gas sensor: pressure too low | warning only | check the plug and the cable, then replace the part |
| F187 | Diverter valve: over-current | switches to backup heating | restart the controller; if it returns, call service |
| F188 | Suction gas sensor: over-current | resets itself after 10 minutes | let the unit cool down and check the air path |
| F189 | Fan 1: over-current | resets itself after 10 minutes | restart the controller; if it returns, call service |
| F190 | Crankcase heater: pressure too low | switches to backup heating | update the firmware |
| F191 | Hot water tank sensor: limit exceeded | warning only | check the setting of the related parameter |
| F192 | Flow sensor: value outside the plausible range | locks the unit until reset at the controller | measure the resistance against the sensor table |
| F193 | High pressure switch: limit not reached in time | resets itself after 10 minutes | check the refrigerant circuit for leaks (certified staff only) |
| F194 | Hot water tank sensor: phase missing | warning only | measure the resistance against the sensor table |
| F195 | Fan 2: sensor short circuit | warning only | restart the controller; if it returns, call service |
| F196 | Circulation pump: configuration mismatch | locks the unit until reset by service | restart the controller; if it returns, call service |
| F197 | Fan 2: over-current | resets itself | restart the controller; if it returns, call service |
| F198 | Discharge gas sensor: contact did not close | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F199 | Controller board: configuration mismatch | locks the unit until reset by service | replace the part |
| F200 | Crankcase heater: over-temperature | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F201 | Hot water tank sensor: contact did not close | switches to backup heating | check the refrigerant circuit for leaks (certified staff only) |
| F202 | Compressor: value outside the plausible range | switches to backup heating | check the plug and the cable, then replace the part |
| F203 | Backup heater: over-current | resets itself after 10 minutes | replace the part |
| F204 | Crankcase heater: checksum error | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F205 | High pressure switch: over-temperature | locks the unit until reset at the controller | check the supply and the fuses |
| F206 | Fan 2: pressure too low | resets itself after 10 minutes | check the setting of the related parameter |
| F207 | Fan 1: limit not reached in time | switches to backup heating | check the plug and the cable, then replace the part |
| F208 | Compressor: checksum error | warning only | replace the part |
| F209 | Low pressure transducer: over-temperature | locks the unit until reset by service | update the firmware |
| F210 | High pressure switch: phase missing | locks the unit until reset at the controller | check the refrigerant circuit for leaks (certified staff only) |
| F211 | Condensate heater: flow too low | warning only | check the plug and the cable, then replace the part |
| F212 | Defrost ended on time limit: not enough energy in the water circuit | warning; after 3 in a row the unit switches to backup heating | check the buffer volume and the flow; see the installation manual, section 6 |
| F213 | Inverter: value outside the plausible range | locks the unit until reset by service | measure the resistance against the sensor table |
| F214 | Flow meter: phase missing | locks the unit until reset at the controller | clean the strainer and bleed the circuit |
| F215 | Fan 1: limit exceeded | locks the unit until reset by service | replace the part |
| F216 | Compressor: limit exceeded | resets itself after 10 minutes | check the refrigerant circuit for leaks (certified staff only) |
| F217 | Four-way valve: contact did not close | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F218 | Return sensor: phase missing | locks the unit until reset by service | check the refrigerant circuit for leaks (certified staff only) |
| F219 | Compressor: flow too low | resets itself | check the refrigerant circuit for leaks (certified staff only) |
| F220 | Outdoor air sensor: limit not reached in time | warning only | replace the part |
| F221 | Condensate heater: pressure too low | warning only | clean the strainer and bleed the circuit |
| F222 | Fan 2: sensor short circuit | locks the unit until reset at the controller | update the firmware |
| F223 | Inverter: flow too low | resets itself | let the unit cool down and check the air path |
| F224 | Fan 2: configuration mismatch | switches to backup heating | clean the strainer and bleed the circuit |
| F225 | Hot water tank sensor: value outside the plausible range | switches to backup heating | check the plug and the cable, then replace the part |
| F226 | Return sensor: contact did not open | locks the unit until reset at the controller | let the unit cool down and check the air path |
| F227 | Controller board: configuration mismatch | resets itself | check the supply and the fuses |
| F228 | Fan 1: flow too low | resets itself | replace the part |
| F229 | Controller board: over-temperature | locks the unit until reset by service | replace the part |
| F230 | Crankcase heater: contact did not open | resets itself after 10 minutes | restart the controller; if it returns, call service |
| F231 | Fan 2: sensor open circuit | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F232 | Hot water tank sensor: configuration mismatch | locks the unit until reset by service | check the supply and the fuses |
| F233 | Discharge gas sensor: limit exceeded | locks the unit until reset at the controller | replace the part |
| F234 | Flow meter: phase missing | switches to backup heating | measure the resistance against the sensor table |
| F235 | Circulation pump: configuration mismatch | resets itself after 10 minutes | measure the resistance against the sensor table |
| F236 | Outdoor air sensor: phase missing | locks the unit until reset at the controller | check the supply and the fuses |
| F237 | Fan 1: limit exceeded | resets itself after 10 minutes | check the plug and the cable, then replace the part |
| F238 | Four-way valve: limit not reached in time | locks the unit until reset by service | measure the resistance against the sensor table |
| F239 | Compressor: limit exceeded | resets itself | check the plug and the cable, then replace the part |
| F240 | Fan 2: limit exceeded | resets itself | update the firmware |
| F241 | Four-way valve: pressure too low | resets itself after 10 minutes | clean the strainer and bleed the circuit |
| F242 | Circulation pump: value outside the plausible range | switches to backup heating | measure the resistance against the sensor table |
| F243 | Mixing valve: sensor open circuit | switches to backup heating | clean the strainer and bleed the circuit |
| F244 | Crankcase heater: flow too low | switches to backup heating | check the supply and the fuses |
| F245 | Outdoor air sensor: over-temperature | locks the unit until reset at the controller | replace the part |
| F246 | Fan 1: phase missing | resets itself | restart the controller; if it returns, call service |
| F247 | Expansion valve: limit not reached in time | locks the unit until reset by service | replace the part |
| F248 | High pressure switch: sensor short circuit | switches to backup heating | measure the resistance against the sensor table |
| F249 | Flow sensor: sensor open circuit | resets itself after 10 minutes | clean the strainer and bleed the circuit |
| F250 | Flow sensor: phase missing | locks the unit until reset by service | update the firmware |
| F251 | High pressure switch: sensor open circuit | warning only | update the firmware |
| F252 | Diverter valve: contact did not open | locks the unit until reset at the controller | check the setting of the related parameter |
| F253 | Expansion valve: over-current | resets itself | check the setting of the related parameter |
| F254 | Bus module: over-temperature | switches to backup heating | let the unit cool down and check the air path |
| F255 | Backup heater: pressure too high | warning only | check the supply and the fuses |
| F256 | Return sensor: over-temperature | resets itself | clean the strainer and bleed the circuit |
| F257 | Hot water tank sensor: checksum error | locks the unit until reset at the controller | clean the strainer and bleed the circuit |
| F258 | Compressor: pressure too high | warning only | update the firmware |
| F259 | Suction gas sensor: sensor short circuit | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F260 | Suction gas sensor: contact did not open | warning only | clean the strainer and bleed the circuit |
| F261 | High pressure switch: flow too low | warning only | restart the controller; if it returns, call service |
| F262 | Controller board: over-temperature | resets itself after 10 minutes | check the setting of the related parameter |
| F263 | Outdoor air sensor: phase missing | warning only | check the plug and the cable, then replace the part |
| F264 | Controller board: flow too low | resets itself | check the refrigerant circuit for leaks (certified staff only) |
| F265 | Crankcase heater: pressure too high | resets itself after 10 minutes | check the plug and the cable, then replace the part |
| F266 | Condensate heater: checksum error | switches to backup heating | check the supply and the fuses |
| F267 | Mixing valve: value outside the plausible range | locks the unit until reset by service | check the setting of the related parameter |
| F268 | High pressure switch: limit not reached in time | locks the unit until reset at the controller | check the setting of the related parameter |
| F269 | Circulation pump: over-current | resets itself after 10 minutes | check the plug and the cable, then replace the part |
| F270 | Expansion valve: configuration mismatch | resets itself | check the plug and the cable, then replace the part |
| F271 | Low pressure transducer: checksum error | switches to backup heating | restart the controller; if it returns, call service |
| F272 | Circulation pump: pressure too low | warning only | check the plug and the cable, then replace the part |
| F273 | High pressure switch: value outside the plausible range | warning only | clean the strainer and bleed the circuit |
| F274 | Inverter: sensor short circuit | warning only | restart the controller; if it returns, call service |
| F275 | Inverter: no communication | resets itself after 10 minutes | check the setting of the related parameter |
| F276 | Diverter valve: phase missing | locks the unit until reset at the controller | check the plug and the cable, then replace the part |
| F277 | Circulation pump: over-current | switches to backup heating | restart the controller; if it returns, call service |
| F278 | Return sensor: pressure too high | locks the unit until reset by service | check the supply and the fuses |
| F279 | Four-way valve: contact did not open | warning only | restart the controller; if it returns, call service |
| F280 | Flow meter: value outside the plausible range | warning only | check the setting of the related parameter |
| F281 | High pressure switch: sensor open circuit | switches to backup heating | let the unit cool down and check the air path |
| F282 | Mixing valve: pressure too high | warning only | replace the part |
| F283 | Inverter: sensor open circuit | resets itself after 10 minutes | measure the resistance against the sensor table |
| F284 | Discharge gas sensor: flow too low | locks the unit until reset at the controller | check the plug and the cable, then replace the part |
| F285 | Return sensor: configuration mismatch | warning only | let the unit cool down and check the air path |
| F286 | Diverter valve: no communication | locks the unit until reset at the controller | check the plug and the cable, then replace the part |
| F287 | Flow sensor: checksum error | resets itself | measure the resistance against the sensor table |
| F288 | Buffer sensor: configuration mismatch | resets itself after 10 minutes | restart the controller; if it returns, call service |
| F289 | Hot water tank sensor: sensor open circuit | resets itself | check the refrigerant circuit for leaks (certified staff only) |
| F290 | High pressure switch: flow too low | resets itself | check the setting of the related parameter |
| F291 | Flow meter: sensor short circuit | resets itself after 10 minutes | measure the resistance against the sensor table |
| F292 | Crankcase heater: pressure too low | warning only | replace the part |
| F293 | Compressor: limit exceeded | resets itself | clean the strainer and bleed the circuit |
| F294 | Fan 2: over-temperature | switches to backup heating | update the firmware |
| F295 | Outdoor air sensor: configuration mismatch | locks the unit until reset by service | check the supply and the fuses |
| F296 | Fan 1: flow too low | resets itself | replace the part |
| F297 | Expansion valve: limit exceeded | locks the unit until reset at the controller | check the supply and the fuses |
| F298 | Backup heater: sensor open circuit | locks the unit until reset by service | let the unit cool down and check the air path |
| F299 | Four-way valve: sensor short circuit | warning only | check the setting of the related parameter |
| F300 | Diverter valve: pressure too low | switches to backup heating | clean the strainer and bleed the circuit |
| F301 | Refrigerant leak detector alarm | locks the unit, runs the fans at full speed, opens the alarm contact | leave the safety zone, remove ignition sources, call certified service; do not reset |
| F302 | Flow sensor: contact did not open | locks the unit until reset by service | measure the resistance against the sensor table |
| F303 | Backup heater: contact did not open | resets itself after 10 minutes | restart the controller; if it returns, call service |
| F304 | Flow sensor: over-temperature | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F305 | Expansion valve: pressure too high | locks the unit until reset at the controller | measure the resistance against the sensor table |
| F306 | Circulation pump: limit exceeded | resets itself | measure the resistance against the sensor table |
| F307 | Outdoor air sensor: no communication | resets itself after 10 minutes | clean the strainer and bleed the circuit |
| F308 | Mixing valve: over-current | locks the unit until reset by service | restart the controller; if it returns, call service |
| F309 | Condensate heater: flow too low | locks the unit until reset by service | update the firmware |
| F310 | Fan 1: configuration mismatch | resets itself after 10 minutes | update the firmware |
| F311 | Crankcase heater: limit not reached in time | warning only | update the firmware |
| F312 | Low pressure transducer: sensor short circuit | switches to backup heating | restart the controller; if it returns, call service |
| F313 | Four-way valve: flow too low | resets itself | restart the controller; if it returns, call service |
| F314 | Mixing valve: no communication | switches to backup heating | update the firmware |
| F315 | High pressure switch: no communication | locks the unit until reset by service | check the plug and the cable, then replace the part |
| F316 | Backup heater: no communication | locks the unit until reset by service | update the firmware |
| F317 | Suction gas sensor: over-temperature | warning only | check the plug and the cable, then replace the part |
| F318 | Backup heater: pressure too high | locks the unit until reset at the controller | check the refrigerant circuit for leaks (certified staff only) |
| F319 | Hot water tank sensor: contact did not close | warning only | check the plug and the cable, then replace the part |
| F320 | Diverter valve: no communication | switches to backup heating | check the setting of the related parameter |
| F321 | Return sensor: flow too low | warning only | let the unit cool down and check the air path |
| F322 | Outdoor air sensor: sensor open circuit | switches to backup heating | restart the controller; if it returns, call service |
| F323 | Four-way valve: sensor open circuit | resets itself | check the refrigerant circuit for leaks (certified staff only) |
| F324 | Flow sensor: contact did not open | resets itself after 10 minutes | check the plug and the cable, then replace the part |
| F325 | Inverter: checksum error | resets itself after 10 minutes | replace the part |
| F326 | High pressure switch: pressure too low | warning only | check the supply and the fuses |
| F327 | Expansion valve: pressure too low | switches to backup heating | check the supply and the fuses |
| F328 | Compressor: no communication | switches to backup heating | let the unit cool down and check the air path |
| F329 | Inverter: over-current | resets itself after 10 minutes | check the setting of the related parameter |
| F330 | Discharge gas sensor: value outside the plausible range | locks the unit until reset by service | check the refrigerant circuit for leaks (certified staff only) |
| F331 | Mixing valve: flow too low | switches to backup heating | check the refrigerant circuit for leaks (certified staff only) |
| F332 | Compressor: limit exceeded | warning only | measure the resistance against the sensor table |
| F333 | High pressure switch: sensor open circuit | locks the unit until reset at the controller | check the supply and the fuses |
| F334 | Mixing valve: phase missing | switches to backup heating | update the firmware |
| F335 | High pressure switch: no communication | resets itself after 10 minutes | check the supply and the fuses |
| F336 | Circulation pump: pressure too low | resets itself after 10 minutes | measure the resistance against the sensor table |
| F337 | Flow sensor: over-temperature | locks the unit until reset at the controller | check the refrigerant circuit for leaks (certified staff only) |
| F338 | Buffer sensor: pressure too high | resets itself | let the unit cool down and check the air path |
| F339 | Backup heater: pressure too high | locks the unit until reset by service | check the refrigerant circuit for leaks (certified staff only) |
| F340 | Circulation pump: value outside the plausible range | resets itself after 10 minutes | let the unit cool down and check the air path |
| F341 | Flow sensor: pressure too high | resets itself after 10 minutes | let the unit cool down and check the air path |
| F342 | Controller board: checksum error | resets itself | let the unit cool down and check the air path |
| F343 | Fan 2: flow too low | warning only | measure the resistance against the sensor table |
| F344 | Inverter: contact did not close | switches to backup heating | check the setting of the related parameter |
| F345 | Fan 1: contact did not close | switches to backup heating | check the setting of the related parameter |
| F346 | Discharge gas sensor: value outside the plausible range | resets itself | check the supply and the fuses |
| F347 | Flow meter: contact did not open | resets itself after 10 minutes | check the setting of the related parameter |
| F348 | Controller board: contact did not open | switches to backup heating | replace the part |
| F349 | Suction gas sensor: phase missing | switches to backup heating | update the firmware |
| F350 | Fan 2: contact did not close | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F351 | Controller board: configuration mismatch | switches to backup heating | clean the strainer and bleed the circuit |
| F352 | Circulation pump: checksum error | resets itself | check the setting of the related parameter |
| F353 | Return sensor: limit exceeded | switches to backup heating | check the refrigerant circuit for leaks (certified staff only) |
| F354 | Discharge gas sensor: pressure too low | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F355 | Return sensor: limit not reached in time | locks the unit until reset by service | let the unit cool down and check the air path |
| F356 | Discharge gas sensor: pressure too high | locks the unit until reset at the controller | restart the controller; if it returns, call service |
| F357 | Return sensor: configuration mismatch | switches to backup heating | check the setting of the related parameter |
| F358 | Inverter: over-current | resets itself | update the firmware |
| F359 | Discharge gas sensor: contact did not open | switches to backup heating | check the supply and the fuses |
| F360 | Circulation pump: sensor short circuit | locks the unit until reset by service | let the unit cool down and check the air path |
| F361 | Four-way valve: value outside the plausible range | resets itself | clean the strainer and bleed the circuit |
| F362 | Hot water tank sensor: contact did not open | switches to backup heating | let the unit cool down and check the air path |
| F363 | Bus module: contact did not close | resets itself | check the supply and the fuses |
| F364 | Backup heater: checksum error | resets itself | check the plug and the cable, then replace the part |
| F365 | Low pressure transducer: pressure too high | switches to backup heating | check the plug and the cable, then replace the part |
| F366 | Suction gas sensor: phase missing | locks the unit until reset at the controller | check the supply and the fuses |
| F367 | Four-way valve: limit exceeded | resets itself | replace the part |
| F368 | Inverter: limit not reached in time | locks the unit until reset by service | replace the part |
| F369 | Expansion valve: sensor open circuit | locks the unit until reset at the controller | check the supply and the fuses |
| F370 | Diverter valve: pressure too high | locks the unit until reset at the controller | update the firmware |
| F371 | Low pressure transducer: over-temperature | resets itself | check the refrigerant circuit for leaks (certified staff only) |
| F372 | High pressure switch: limit not reached in time | switches to backup heating | replace the part |
| F373 | Condensate heater: pressure too low | resets itself after 10 minutes | check the supply and the fuses |
| F374 | Controller board: contact did not close | switches to backup heating | update the firmware |
| F375 | Crankcase heater: pressure too high | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F376 | Circulation pump: pressure too high | warning only | let the unit cool down and check the air path |
| F377 | Buffer sensor: flow too low | locks the unit until reset by service | let the unit cool down and check the air path |
| F378 | Fan 2: over-current | warning only | check the supply and the fuses |
| F379 | Expansion valve: checksum error | warning only | let the unit cool down and check the air path |
| F380 | Crankcase heater: phase missing | locks the unit until reset by service | check the setting of the related parameter |
| F381 | Inverter: over-current | locks the unit until reset by service | check the supply and the fuses |
| F382 | Four-way valve: limit exceeded | locks the unit until reset by service | restart the controller; if it returns, call service |
| F383 | Bus module: flow too low | switches to backup heating | clean the strainer and bleed the circuit |
| F384 | High pressure switch: configuration mismatch | resets itself | measure the resistance against the sensor table |
| F385 | Outdoor air sensor: phase missing | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F386 | Crankcase heater: value outside the plausible range | locks the unit until reset by service | replace the part |
| F387 | Low pressure transducer: contact did not close | switches to backup heating | measure the resistance against the sensor table |
| F388 | Compressor: limit not reached in time | resets itself after 10 minutes | replace the part |
| F389 | Backup heater: no communication | locks the unit until reset by service | check the supply and the fuses |
| F390 | Flow meter: sensor open circuit | warning only | check the setting of the related parameter |
| F391 | Compressor: flow too low | warning only | let the unit cool down and check the air path |
| F392 | Mixing valve: phase missing | resets itself | restart the controller; if it returns, call service |
| F393 | Diverter valve: contact did not close | resets itself after 10 minutes | check the supply and the fuses |
| F394 | Discharge gas sensor: sensor short circuit | locks the unit until reset by service | check the refrigerant circuit for leaks (certified staff only) |
| F395 | Outdoor air sensor: pressure too low | locks the unit until reset by service | check the refrigerant circuit for leaks (certified staff only) |
| F396 | Mixing valve: sensor open circuit | resets itself after 10 minutes | replace the part |
| F397 | Buffer sensor: flow too low | locks the unit until reset by service | update the firmware |
| F398 | Discharge gas sensor: value outside the plausible range | resets itself | let the unit cool down and check the air path |
| F399 | Suction gas sensor: over-current | resets itself after 10 minutes | restart the controller; if it returns, call service |
| F400 | Inverter: limit not reached in time | resets itself | let the unit cool down and check the air path |
| F401 | Buffer sensor: sensor short circuit | locks the unit until reset at the controller | check the setting of the related parameter |
| F402 | Discharge gas sensor: over-current | resets itself | restart the controller; if it returns, call service |
| F403 | Fan 1: flow too low | warning only | check the refrigerant circuit for leaks (certified staff only) |
| F404 | Bus module: pressure too high | resets itself after 10 minutes | let the unit cool down and check the air path |
| F405 | Return sensor: phase missing | switches to backup heating | check the setting of the related parameter |
| F406 | Outdoor air sensor: pressure too low | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F407 | Hot water tank sensor: no communication | locks the unit until reset at the controller | check the setting of the related parameter |
| F408 | Buffer sensor: over-temperature | resets itself after 10 minutes | measure the resistance against the sensor table |
| F409 | Suction gas sensor: over-temperature | switches to backup heating | let the unit cool down and check the air path |
| F410 | Diverter valve: contact did not open | switches to backup heating | update the firmware |
| F411 | Return sensor: over-current | warning only | check the plug and the cable, then replace the part |
| F412 | Buffer sensor: configuration mismatch | warning only | clean the strainer and bleed the circuit |
| F413 | Outdoor air sensor: pressure too low | switches to backup heating | replace the part |
| F414 | Controller board: contact did not close | resets itself after 10 minutes | clean the strainer and bleed the circuit |
| F415 | Hot water tank sensor: sensor open circuit | resets itself | check the plug and the cable, then replace the part |
| F416 | Hot water tank sensor: pressure too high | warning only | update the firmware |
| F417 | Crankcase heater: sensor short circuit | switches to backup heating | update the firmware |
| F418 | Flow sensor: over-temperature | locks the unit until reset by service | clean the strainer and bleed the circuit |
| F419 | Bus module: over-current | switches to backup heating | check the setting of the related parameter |

## The faults in detail


**F100 Discharge gas sensor: over-temperature.** The unit locks the unit until reset by service. Seen most often on units older than 5 years. First check: clean the strainer and bleed the circuit. Typical values when it appears: suction pressure below 18. Part usually needed: VP-12102. Time allowed under warranty: 30 minutes.

**F101 Buffer sensor: limit not reached in time.** The unit resets itself. Seen most often on units older than 5 years. First check: replace the part. Typical values when it appears: return temperature below 2.5. Part usually needed: VP-11608. Time allowed under warranty: 45 minutes.

**F102 Crankcase heater: over-current.** The unit locks the unit until reset at the controller. Seen most often in cascades. First check: check the supply and the fuses. Typical values when it appears: discharge temperature above 0.8. Part usually needed: VP-15115. Time allowed under warranty: 20 minutes.

**F103 Discharge gas sensor: value outside the plausible range.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: discharge temperature below 18. Part usually needed: VP-14693. Time allowed under warranty: 20 minutes.

**F104 Hot water tank sensor: flow too low.** The unit locks the unit until reset at the controller. Seen most often in the first weeks after commissioning. First check: check the supply and the fuses. Typical values when it appears: return temperature below 440. Part usually needed: VP-10823. Time allowed under warranty: 20 minutes.

**F105 Mixing valve: limit not reached in time.** The unit warning only. Seen most often in cascades. First check: clean the strainer and bleed the circuit. Typical values when it appears: flow below 2.5. Part usually needed: VP-10510. Time allowed under warranty: 90 minutes.

**F106 Circulation pump: phase missing.** The unit resets itself after 10 minutes. Seen most often in the first weeks after commissioning. First check: check the plug and the cable, then replace the part. Typical values when it appears: flow above 3. Part usually needed: VP-13816. Time allowed under warranty: 45 minutes.

**F107 Outdoor air sensor: value outside the plausible range.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature below 2.5. Part usually needed: VP-14319. Time allowed under warranty: 20 minutes.

**F108 Backup heater: limit exceeded.** The unit warning only. Seen most often after work on the water side. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: discharge temperature below 2.5. Part usually needed: VP-11092. Time allowed under warranty: 30 minutes.

**F109 Bus module: pressure too low.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: check the setting of the related parameter. Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-12074. Time allowed under warranty: 20 minutes.

**F110 Mixing valve: contact did not close.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: restart the controller; if it returns, call service. Typical values when it appears: supply voltage below 1.2. Part usually needed: VP-11358. Time allowed under warranty: 90 minutes.

**F111 Crankcase heater: pressure too low.** The unit switches to backup heating. Seen most often in summer during hot water. First check: clean the strainer and bleed the circuit. Typical values when it appears: suction pressure below 95. Part usually needed: VP-12934. Time allowed under warranty: 90 minutes.

**F112 Low pressure transducer: limit exceeded.** The unit warning only. Seen most often on units older than 5 years. First check: measure the resistance against the sensor table. Typical values when it appears: flow below 1.2. Part usually needed: VP-10846. Time allowed under warranty: 90 minutes.

**F113 Crankcase heater: limit exceeded.** The unit resets itself. Seen most often in summer during hot water. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-12086. Time allowed under warranty: 30 minutes.

**F114 Compressor: contact did not open.** The unit resets itself after 10 minutes. Seen most often in summer during hot water. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure below 1.2. Part usually needed: VP-11480. Time allowed under warranty: 30 minutes.

**F115 Return sensor: limit exceeded.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature above 3. Part usually needed: VP-14358. Time allowed under warranty: 45 minutes.

**F116 High pressure switch: sensor open circuit.** The unit switches to backup heating. Seen most often in frost. First check: update the firmware. Typical values when it appears: supply voltage above 2.5. Part usually needed: VP-14046. Time allowed under warranty: 45 minutes.

**F117 Low pressure transducer: over-current.** The unit resets itself after 10 minutes. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature below 18. Part usually needed: VP-13122. Time allowed under warranty: 20 minutes.

**F118 Buffer sensor: checksum error.** The unit switches to backup heating. Seen most often after a power cut. First check: check the setting of the related parameter. Typical values when it appears: discharge temperature above 18. Part usually needed: VP-11605. Time allowed under warranty: 30 minutes.

**F119 Low pressure transducer: no communication.** The unit warning only. Seen most often in frost. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: flow above 110. Part usually needed: VP-14434. Time allowed under warranty: 20 minutes.

**F120 Mixing valve: flow too low.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: flow above 110. Part usually needed: VP-11062. Time allowed under warranty: 20 minutes.

**F121 Condensate heater: checksum error.** The unit resets itself after 10 minutes. Seen most often after work on the water side. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: return temperature above 95. Part usually needed: VP-10444. Time allowed under warranty: 60 minutes.

**F122 Discharge gas sensor: flow too low.** The unit locks the unit until reset by service. Seen most often in the first weeks after commissioning. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature above 0.8. Part usually needed: VP-15340. Time allowed under warranty: 30 minutes.

**F123 Flow sensor: limit not reached in time.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: discharge temperature above 110. Part usually needed: VP-12234. Time allowed under warranty: 60 minutes.

**F124 Bus module: contact did not close.** The unit resets itself after 10 minutes. Seen most often in summer during hot water. First check: clean the strainer and bleed the circuit. Typical values when it appears: supply voltage above 3. Part usually needed: VP-15329. Time allowed under warranty: 90 minutes.

**F125 Compressor: sensor open circuit.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: return temperature above 0.8. Part usually needed: VP-13945. Time allowed under warranty: 45 minutes.

**F126 Suction gas sensor: limit exceeded.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature below 95. Part usually needed: VP-11164. Time allowed under warranty: 20 minutes.

**F127 Low pressure transducer: limit not reached in time.** The unit resets itself after 10 minutes. Seen most often in summer during hot water. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure below 360. Part usually needed: VP-10413. Time allowed under warranty: 60 minutes.

**F128 Flow sensor: no communication.** The unit resets itself. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: discharge temperature above 440. Part usually needed: VP-11654. Time allowed under warranty: 60 minutes.

**F129 Fan 2: over-temperature.** The unit warning only. Seen most often in cascades. First check: check the setting of the related parameter. Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-10120. Time allowed under warranty: 30 minutes.

**F130 Flow sensor: contact did not close.** The unit switches to backup heating. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: return temperature above 3. Part usually needed: VP-11296. Time allowed under warranty: 45 minutes.

**F131 Backup heater: sensor open circuit.** The unit resets itself. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: discharge temperature above 3. Part usually needed: VP-11629. Time allowed under warranty: 45 minutes.

**F132 Backup heater: contact did not open.** The unit locks the unit until reset by service. Seen most often after work on the water side. First check: measure the resistance against the sensor table. Typical values when it appears: suction pressure below 95. Part usually needed: VP-10066. Time allowed under warranty: 90 minutes.

**F133 Controller board: pressure too low.** The unit switches to backup heating. Seen most often in summer during hot water. First check: check the supply and the fuses. Typical values when it appears: supply voltage below 1.2. Part usually needed: VP-15134. Time allowed under warranty: 30 minutes.

**F134 Circulation pump: over-temperature.** The unit switches to backup heating. Seen most often in frost. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature below 3. Part usually needed: VP-13666. Time allowed under warranty: 60 minutes.

**F135 Outdoor air sensor: contact did not close.** The unit locks the unit until reset by service. Seen most often in cascades. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature above 110. Part usually needed: VP-11604. Time allowed under warranty: 20 minutes.

**F136 Inverter: flow too low.** The unit warning only. Seen most often after work on the water side. First check: restart the controller; if it returns, call service. Typical values when it appears: flow above 1.2. Part usually needed: VP-11753. Time allowed under warranty: 20 minutes.

**F137 Flow meter: checksum error.** The unit locks the unit until reset at the controller. Seen most often in cascades. First check: clean the strainer and bleed the circuit. Typical values when it appears: supply voltage below 95. Part usually needed: VP-13672. Time allowed under warranty: 20 minutes.

**F138 Flow sensor: configuration mismatch.** The unit resets itself. Seen most often in frost. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature above 95. Part usually needed: VP-14980. Time allowed under warranty: 45 minutes.

**F139 Suction gas sensor: pressure too high.** The unit switches to backup heating. Seen most often after work on the water side. First check: restart the controller; if it returns, call service. Typical values when it appears: discharge temperature above 360. Part usually needed: VP-11740. Time allowed under warranty: 60 minutes.

**F140 Circulation pump: phase missing.** The unit resets itself. Seen most often in frost. First check: restart the controller; if it returns, call service. Typical values when it appears: return temperature above 21. Part usually needed: VP-13385. Time allowed under warranty: 30 minutes.

**F141 Circulation pump: contact did not close.** The unit resets itself. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: flow below 2.5. Part usually needed: VP-13718. Time allowed under warranty: 30 minutes.

**F142 Fan 2: sensor open circuit.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: check the setting of the related parameter. Typical values when it appears: flow above 360. Part usually needed: VP-13077. Time allowed under warranty: 20 minutes.

**F143 Inverter: over-current.** The unit switches to backup heating. Seen most often after work on the water side. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature below 110. Part usually needed: VP-10488. Time allowed under warranty: 45 minutes.

**F144 High pressure switch: over-current.** The unit warning only. Seen most often in the first weeks after commissioning. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature below 1.2. Part usually needed: VP-10611. Time allowed under warranty: 45 minutes.

**F145 High pressure switch: configuration mismatch.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: check the setting of the related parameter. Typical values when it appears: return temperature above 21. Part usually needed: VP-11031. Time allowed under warranty: 90 minutes.

**F146 High pressure switch: over-temperature.** The unit locks the unit until reset at the controller. Seen most often after work on the water side. First check: let the unit cool down and check the air path. Typical values when it appears: supply voltage above 18. Part usually needed: VP-11969. Time allowed under warranty: 90 minutes.

**F148 Diverter valve: no communication.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure below 18. Part usually needed: VP-10733. Time allowed under warranty: 20 minutes.

**F149 Buffer sensor: value outside the plausible range.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: measure the resistance against the sensor table. Typical values when it appears: flow below 18. Part usually needed: VP-15486. Time allowed under warranty: 30 minutes.

**F150 Flow meter: flow too low.** The unit warning only. Seen most often in cascades. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature below 0.8. Part usually needed: VP-11269. Time allowed under warranty: 90 minutes.

**F151 Bus module: sensor short circuit.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: update the firmware. Typical values when it appears: flow below 1.2. Part usually needed: VP-12036. Time allowed under warranty: 20 minutes.

**F152 Flow meter: flow too low.** The unit warning only. Seen most often in cascades. First check: clean the strainer and bleed the circuit. Typical values when it appears: supply voltage above 1.2. Part usually needed: VP-10498. Time allowed under warranty: 90 minutes.

**F153 Compressor: value outside the plausible range.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: update the firmware. Typical values when it appears: supply voltage below 2.5. Part usually needed: VP-13781. Time allowed under warranty: 20 minutes.

**F154 Buffer sensor: pressure too high.** The unit resets itself. Seen most often on units older than 5 years. First check: check the setting of the related parameter. Typical values when it appears: flow above 21. Part usually needed: VP-13119. Time allowed under warranty: 90 minutes.

**F155 Suction gas sensor: limit not reached in time.** The unit locks the unit until reset by service. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: discharge temperature above 1.2. Part usually needed: VP-14675. Time allowed under warranty: 30 minutes.

**F156 Fan 2: contact did not close.** The unit warning only. Seen most often in the first weeks after commissioning. First check: replace the part. Typical values when it appears: supply voltage below 0.8. Part usually needed: VP-10978. Time allowed under warranty: 45 minutes.

**F157 Bus module: no communication.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: update the firmware. Typical values when it appears: return temperature above 0.8. Part usually needed: VP-14754. Time allowed under warranty: 45 minutes.

**F158 Buffer sensor: pressure too low.** The unit switches to backup heating. Seen most often after work on the water side. First check: let the unit cool down and check the air path. Typical values when it appears: flow below 18. Part usually needed: VP-13086. Time allowed under warranty: 20 minutes.

**F159 Fan 1: limit exceeded.** The unit warning only. Seen most often on units older than 5 years. First check: check the setting of the related parameter. Typical values when it appears: suction pressure below 18. Part usually needed: VP-15478. Time allowed under warranty: 60 minutes.

**F160 Return sensor: pressure too high.** The unit resets itself. Seen most often in summer during hot water. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature above 3. Part usually needed: VP-12005. Time allowed under warranty: 20 minutes.

**F161 Hot water tank sensor: sensor short circuit.** The unit locks the unit until reset by service. Seen most often in cascades. First check: let the unit cool down and check the air path. Typical values when it appears: suction pressure above 18. Part usually needed: VP-11264. Time allowed under warranty: 30 minutes.

**F162 Suction gas sensor: phase missing.** The unit locks the unit until reset at the controller. Seen most often on units older than 5 years. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure below 95. Part usually needed: VP-12092. Time allowed under warranty: 90 minutes.

**F163 Compressor: over-current.** The unit warning only. Seen most often in summer during hot water. First check: check the setting of the related parameter. Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-12080. Time allowed under warranty: 60 minutes.

**F164 Low pressure transducer: phase missing.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: suction pressure above 440. Part usually needed: VP-10156. Time allowed under warranty: 30 minutes.

**F165 High pressure switch: pressure too low.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: check the plug and the cable, then replace the part. Typical values when it appears: return temperature above 18. Part usually needed: VP-15456. Time allowed under warranty: 90 minutes.

**F166 Flow meter: flow too low.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: check the setting of the related parameter. Typical values when it appears: flow above 360. Part usually needed: VP-13676. Time allowed under warranty: 20 minutes.

**F167 High pressure switch: phase missing.** The unit locks the unit until reset by service. Seen most often in the first weeks after commissioning. First check: clean the strainer and bleed the circuit. Typical values when it appears: flow above 18. Part usually needed: VP-15931. Time allowed under warranty: 60 minutes.

**F168 Flow meter: flow too low.** The unit warning only. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: flow above 2.5. Part usually needed: VP-14432. Time allowed under warranty: 45 minutes.

**F169 Bus module: contact did not open.** The unit resets itself. Seen most often in summer during hot water. First check: update the firmware. Typical values when it appears: suction pressure below 3. Part usually needed: VP-13315. Time allowed under warranty: 20 minutes.

**F170 High pressure switch: pressure too high.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: replace the part. Typical values when it appears: supply voltage above 110. Part usually needed: VP-15579. Time allowed under warranty: 60 minutes.

**F171 Condensate heater: limit exceeded.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure above 110. Part usually needed: VP-11861. Time allowed under warranty: 60 minutes.

**F172 Buffer sensor: no communication.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: supply voltage below 2.5. Part usually needed: VP-13744. Time allowed under warranty: 45 minutes.

**F173 High pressure switch: contact did not open.** The unit locks the unit until reset at the controller. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: supply voltage below 110. Part usually needed: VP-10278. Time allowed under warranty: 30 minutes.

**F174 Return sensor: over-temperature.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature above 21. Part usually needed: VP-14772. Time allowed under warranty: 60 minutes.

**F175 Controller board: configuration mismatch.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: check the setting of the related parameter. Typical values when it appears: supply voltage above 360. Part usually needed: VP-10632. Time allowed under warranty: 90 minutes.

**F176 Mixing valve: over-current.** The unit warning only. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure above 95. Part usually needed: VP-11100. Time allowed under warranty: 45 minutes.

**F177 Fan 1: contact did not open.** The unit locks the unit until reset at the controller. Seen most often on units older than 5 years. First check: update the firmware. Typical values when it appears: suction pressure below 18. Part usually needed: VP-14146. Time allowed under warranty: 20 minutes.

**F178 Fan 2: pressure too low.** The unit locks the unit until reset at the controller. Seen most often in cascades. First check: update the firmware. Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-15022. Time allowed under warranty: 45 minutes.

**F179 Fan 2: value outside the plausible range.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: return temperature above 0.8. Part usually needed: VP-10797. Time allowed under warranty: 60 minutes.

**F180 Controller board: phase missing.** The unit resets itself. Seen most often in cascades. First check: update the firmware. Typical values when it appears: flow above 18. Part usually needed: VP-11661. Time allowed under warranty: 20 minutes.

**F181 Fan 1: flow too low.** The unit locks the unit until reset by service. Seen most often after work on the water side. First check: replace the part. Typical values when it appears: return temperature above 3. Part usually needed: VP-14029. Time allowed under warranty: 20 minutes.

**F182 High pressure switch: limit not reached in time.** The unit switches to backup heating. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: supply voltage above 2.5. Part usually needed: VP-13654. Time allowed under warranty: 90 minutes.

**F183 High pressure switch: limit exceeded.** The unit locks the unit until reset at the controller. Seen most often in the first weeks after commissioning. First check: check the supply and the fuses. Typical values when it appears: flow above 110. Part usually needed: VP-15357. Time allowed under warranty: 20 minutes.

**F184 Backup heater: over-temperature.** The unit switches to backup heating. Seen most often after work on the water side. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: discharge temperature above 18. Part usually needed: VP-13488. Time allowed under warranty: 45 minutes.

**F185 Hot water tank sensor: over-current.** The unit resets itself. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: return temperature above 18. Part usually needed: VP-14055. Time allowed under warranty: 20 minutes.

**F186 Discharge gas sensor: pressure too low.** The unit warning only. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: discharge temperature below 0.8. Part usually needed: VP-16296. Time allowed under warranty: 30 minutes.

**F187 Diverter valve: over-current.** The unit switches to backup heating. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature below 21. Part usually needed: VP-13039. Time allowed under warranty: 20 minutes.

**F188 Suction gas sensor: over-current.** The unit resets itself after 10 minutes. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: suction pressure above 440. Part usually needed: VP-12963. Time allowed under warranty: 30 minutes.

**F189 Fan 1: over-current.** The unit resets itself after 10 minutes. Seen most often after a power cut. First check: check the plug and the cable, then replace the part. Typical values when it appears: flow above 95. Part usually needed: VP-16042. Time allowed under warranty: 30 minutes.

**F190 Crankcase heater: pressure too low.** The unit switches to backup heating. Seen most often in summer during hot water. First check: replace the part. Typical values when it appears: flow below 110. Part usually needed: VP-12861. Time allowed under warranty: 20 minutes.

**F191 Hot water tank sensor: limit exceeded.** The unit warning only. Seen most often after work on the water side. First check: let the unit cool down and check the air path. Typical values when it appears: supply voltage below 440. Part usually needed: VP-13833. Time allowed under warranty: 60 minutes.

**F192 Flow sensor: value outside the plausible range.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: restart the controller; if it returns, call service. Typical values when it appears: flow below 3. Part usually needed: VP-12338. Time allowed under warranty: 45 minutes.

**F193 High pressure switch: limit not reached in time.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure above 110. Part usually needed: VP-10671. Time allowed under warranty: 90 minutes.

**F194 Hot water tank sensor: phase missing.** The unit warning only. Seen most often in the first weeks after commissioning. First check: check the plug and the cable, then replace the part. Typical values when it appears: supply voltage above 95. Part usually needed: VP-13358. Time allowed under warranty: 90 minutes.

**F195 Fan 2: sensor short circuit.** The unit warning only. Seen most often after work on the water side. First check: check the plug and the cable, then replace the part. Typical values when it appears: return temperature below 21. Part usually needed: VP-15983. Time allowed under warranty: 45 minutes.

**F196 Circulation pump: configuration mismatch.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: flow above 95. Part usually needed: VP-14837. Time allowed under warranty: 20 minutes.

**F197 Fan 2: over-current.** The unit resets itself. Seen most often on units older than 5 years. First check: let the unit cool down and check the air path. Typical values when it appears: discharge temperature above 1.2. Part usually needed: VP-13610. Time allowed under warranty: 45 minutes.

**F198 Discharge gas sensor: contact did not close.** The unit warning only. Seen most often in the first weeks after commissioning. First check: check the plug and the cable, then replace the part. Typical values when it appears: return temperature below 110. Part usually needed: VP-13013. Time allowed under warranty: 60 minutes.

**F199 Controller board: configuration mismatch.** The unit locks the unit until reset by service. Seen most often after work on the water side. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: flow below 21. Part usually needed: VP-14818. Time allowed under warranty: 60 minutes.

**F200 Crankcase heater: over-temperature.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: let the unit cool down and check the air path. Typical values when it appears: discharge temperature above 3. Part usually needed: VP-15550. Time allowed under warranty: 90 minutes.

**F201 Hot water tank sensor: contact did not close.** The unit switches to backup heating. Seen most often in summer during hot water. First check: check the setting of the related parameter. Typical values when it appears: discharge temperature above 440. Part usually needed: VP-14297. Time allowed under warranty: 20 minutes.

**F202 Compressor: value outside the plausible range.** The unit switches to backup heating. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: flow below 2.5. Part usually needed: VP-15916. Time allowed under warranty: 90 minutes.

**F203 Backup heater: over-current.** The unit resets itself after 10 minutes. Seen most often after a power cut. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-14587. Time allowed under warranty: 30 minutes.

**F204 Crankcase heater: checksum error.** The unit locks the unit until reset by service. Seen most often in cascades. First check: clean the strainer and bleed the circuit. Typical values when it appears: suction pressure above 21. Part usually needed: VP-14500. Time allowed under warranty: 45 minutes.

**F205 High pressure switch: over-temperature.** The unit locks the unit until reset at the controller. Seen most often on units older than 5 years. First check: restart the controller; if it returns, call service. Typical values when it appears: flow below 360. Part usually needed: VP-14554. Time allowed under warranty: 30 minutes.

**F206 Fan 2: pressure too low.** The unit resets itself after 10 minutes. Seen most often in frost. First check: replace the part. Typical values when it appears: discharge temperature below 2.5. Part usually needed: VP-12421. Time allowed under warranty: 30 minutes.

**F207 Fan 1: limit not reached in time.** The unit switches to backup heating. Seen most often after work on the water side. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature below 18. Part usually needed: VP-13549. Time allowed under warranty: 60 minutes.

**F208 Compressor: checksum error.** The unit warning only. Seen most often on units older than 5 years. First check: update the firmware. Typical values when it appears: discharge temperature below 110. Part usually needed: VP-11463. Time allowed under warranty: 20 minutes.

**F209 Low pressure transducer: over-temperature.** The unit locks the unit until reset by service. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature below 95. Part usually needed: VP-15062. Time allowed under warranty: 60 minutes.

**F210 High pressure switch: phase missing.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: let the unit cool down and check the air path. Typical values when it appears: return temperature above 110. Part usually needed: VP-10606. Time allowed under warranty: 60 minutes.

**F211 Condensate heater: flow too low.** The unit warning only. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature above 95. Part usually needed: VP-13449. Time allowed under warranty: 60 minutes.

**F213 Inverter: value outside the plausible range.** The unit locks the unit until reset by service. Seen most often in cascades. First check: update the firmware. Typical values when it appears: supply voltage below 0.8. Part usually needed: VP-12571. Time allowed under warranty: 60 minutes.

**F214 Flow meter: phase missing.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: restart the controller; if it returns, call service. Typical values when it appears: supply voltage above 0.8. Part usually needed: VP-14994. Time allowed under warranty: 20 minutes.

**F215 Fan 1: limit exceeded.** The unit locks the unit until reset by service. Seen most often in the first weeks after commissioning. First check: restart the controller; if it returns, call service. Typical values when it appears: flow above 21. Part usually needed: VP-11963. Time allowed under warranty: 60 minutes.

**F216 Compressor: limit exceeded.** The unit resets itself after 10 minutes. Seen most often in summer during hot water. First check: check the plug and the cable, then replace the part. Typical values when it appears: suction pressure above 0.8. Part usually needed: VP-13690. Time allowed under warranty: 60 minutes.

**F217 Four-way valve: contact did not close.** The unit warning only. Seen most often after a power cut. First check: restart the controller; if it returns, call service. Typical values when it appears: return temperature above 1.2. Part usually needed: VP-15294. Time allowed under warranty: 60 minutes.

**F218 Return sensor: phase missing.** The unit locks the unit until reset by service. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: discharge temperature below 0.8. Part usually needed: VP-15715. Time allowed under warranty: 20 minutes.

**F219 Compressor: flow too low.** The unit resets itself. Seen most often after a power cut. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature above 21. Part usually needed: VP-10760. Time allowed under warranty: 20 minutes.

**F220 Outdoor air sensor: limit not reached in time.** The unit warning only. Seen most often after work on the water side. First check: let the unit cool down and check the air path. Typical values when it appears: supply voltage above 21. Part usually needed: VP-13296. Time allowed under warranty: 30 minutes.

**F221 Condensate heater: pressure too low.** The unit warning only. Seen most often in frost. First check: restart the controller; if it returns, call service. Typical values when it appears: return temperature above 440. Part usually needed: VP-12945. Time allowed under warranty: 45 minutes.

**F222 Fan 2: sensor short circuit.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: supply voltage below 3. Part usually needed: VP-12627. Time allowed under warranty: 60 minutes.

**F223 Inverter: flow too low.** The unit resets itself. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: flow below 1.2. Part usually needed: VP-15009. Time allowed under warranty: 20 minutes.

**F224 Fan 2: configuration mismatch.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: update the firmware. Typical values when it appears: supply voltage above 18. Part usually needed: VP-10844. Time allowed under warranty: 45 minutes.

**F225 Hot water tank sensor: value outside the plausible range.** The unit switches to backup heating. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: discharge temperature below 360. Part usually needed: VP-13594. Time allowed under warranty: 30 minutes.

**F226 Return sensor: contact did not open.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: restart the controller; if it returns, call service. Typical values when it appears: flow above 1.2. Part usually needed: VP-14165. Time allowed under warranty: 60 minutes.

**F227 Controller board: configuration mismatch.** The unit resets itself. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature above 2.5. Part usually needed: VP-14190. Time allowed under warranty: 45 minutes.

**F228 Fan 1: flow too low.** The unit resets itself. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: flow below 440. Part usually needed: VP-11091. Time allowed under warranty: 20 minutes.

**F229 Controller board: over-temperature.** The unit locks the unit until reset by service. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature below 110. Part usually needed: VP-11426. Time allowed under warranty: 30 minutes.

**F230 Crankcase heater: contact did not open.** The unit resets itself after 10 minutes. Seen most often in the first weeks after commissioning. First check: update the firmware. Typical values when it appears: return temperature above 1.2. Part usually needed: VP-14319. Time allowed under warranty: 60 minutes.

**F231 Fan 2: sensor open circuit.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature above 18. Part usually needed: VP-13785. Time allowed under warranty: 60 minutes.

**F232 Hot water tank sensor: configuration mismatch.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: return temperature above 3. Part usually needed: VP-13163. Time allowed under warranty: 45 minutes.

**F233 Discharge gas sensor: limit exceeded.** The unit locks the unit until reset at the controller. Seen most often in the first weeks after commissioning. First check: replace the part. Typical values when it appears: discharge temperature below 95. Part usually needed: VP-14106. Time allowed under warranty: 45 minutes.

**F234 Flow meter: phase missing.** The unit switches to backup heating. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: flow above 3. Part usually needed: VP-11979. Time allowed under warranty: 45 minutes.

**F235 Circulation pump: configuration mismatch.** The unit resets itself after 10 minutes. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: suction pressure above 18. Part usually needed: VP-15709. Time allowed under warranty: 45 minutes.

**F236 Outdoor air sensor: phase missing.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature below 360. Part usually needed: VP-15108. Time allowed under warranty: 45 minutes.

**F237 Fan 1: limit exceeded.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: restart the controller; if it returns, call service. Typical values when it appears: flow below 440. Part usually needed: VP-15016. Time allowed under warranty: 20 minutes.

**F238 Four-way valve: limit not reached in time.** The unit locks the unit until reset by service. Seen most often on units older than 5 years. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature above 440. Part usually needed: VP-15161. Time allowed under warranty: 20 minutes.

**F239 Compressor: limit exceeded.** The unit resets itself. Seen most often in cascades. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure below 110. Part usually needed: VP-12586. Time allowed under warranty: 60 minutes.

**F240 Fan 2: limit exceeded.** The unit resets itself. Seen most often in frost. First check: update the firmware. Typical values when it appears: discharge temperature below 2.5. Part usually needed: VP-10494. Time allowed under warranty: 90 minutes.

**F241 Four-way valve: pressure too low.** The unit resets itself after 10 minutes. Seen most often after work on the water side. First check: update the firmware. Typical values when it appears: supply voltage below 2.5. Part usually needed: VP-15274. Time allowed under warranty: 90 minutes.

**F242 Circulation pump: value outside the plausible range.** The unit switches to backup heating. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: suction pressure above 2.5. Part usually needed: VP-15548. Time allowed under warranty: 30 minutes.

**F243 Mixing valve: sensor open circuit.** The unit switches to backup heating. Seen most often after work on the water side. First check: check the supply and the fuses. Typical values when it appears: supply voltage above 95. Part usually needed: VP-14000. Time allowed under warranty: 45 minutes.

**F244 Crankcase heater: flow too low.** The unit switches to backup heating. Seen most often after work on the water side. First check: check the setting of the related parameter. Typical values when it appears: flow above 3. Part usually needed: VP-13654. Time allowed under warranty: 60 minutes.

**F245 Outdoor air sensor: over-temperature.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: check the supply and the fuses. Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-15928. Time allowed under warranty: 90 minutes.

**F246 Fan 1: phase missing.** The unit resets itself. Seen most often after a power cut. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature below 3. Part usually needed: VP-12186. Time allowed under warranty: 60 minutes.

**F247 Expansion valve: limit not reached in time.** The unit locks the unit until reset by service. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: supply voltage above 1.2. Part usually needed: VP-15250. Time allowed under warranty: 60 minutes.

**F248 High pressure switch: sensor short circuit.** The unit switches to backup heating. Seen most often after work on the water side. First check: replace the part. Typical values when it appears: suction pressure below 360. Part usually needed: VP-10968. Time allowed under warranty: 60 minutes.

**F249 Flow sensor: sensor open circuit.** The unit resets itself after 10 minutes. Seen most often after work on the water side. First check: check the setting of the related parameter. Typical values when it appears: flow below 360. Part usually needed: VP-10711. Time allowed under warranty: 30 minutes.

**F250 Flow sensor: phase missing.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: check the supply and the fuses. Typical values when it appears: return temperature below 3. Part usually needed: VP-11625. Time allowed under warranty: 20 minutes.

**F251 High pressure switch: sensor open circuit.** The unit warning only. Seen most often on units older than 5 years. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: flow above 2.5. Part usually needed: VP-10270. Time allowed under warranty: 45 minutes.

**F252 Diverter valve: contact did not open.** The unit locks the unit until reset at the controller. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: flow below 440. Part usually needed: VP-13690. Time allowed under warranty: 45 minutes.

**F253 Expansion valve: over-current.** The unit resets itself. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: return temperature above 360. Part usually needed: VP-10084. Time allowed under warranty: 30 minutes.

**F254 Bus module: over-temperature.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: flow below 95. Part usually needed: VP-12883. Time allowed under warranty: 20 minutes.

**F255 Backup heater: pressure too high.** The unit warning only. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: supply voltage below 0.8. Part usually needed: VP-12755. Time allowed under warranty: 60 minutes.

**F256 Return sensor: over-temperature.** The unit resets itself. Seen most often in summer during hot water. First check: replace the part. Typical values when it appears: suction pressure above 440. Part usually needed: VP-12410. Time allowed under warranty: 45 minutes.

**F257 Hot water tank sensor: checksum error.** The unit locks the unit until reset at the controller. Seen most often after work on the water side. First check: check the setting of the related parameter. Typical values when it appears: suction pressure below 2.5. Part usually needed: VP-13692. Time allowed under warranty: 60 minutes.

**F258 Compressor: pressure too high.** The unit warning only. Seen most often in the first weeks after commissioning. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature below 0.8. Part usually needed: VP-15522. Time allowed under warranty: 45 minutes.

**F259 Suction gas sensor: sensor short circuit.** The unit warning only. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: flow above 3. Part usually needed: VP-15759. Time allowed under warranty: 90 minutes.

**F260 Suction gas sensor: contact did not open.** The unit warning only. Seen most often in the first weeks after commissioning. First check: check the setting of the related parameter. Typical values when it appears: discharge temperature below 2.5. Part usually needed: VP-12090. Time allowed under warranty: 90 minutes.

**F261 High pressure switch: flow too low.** The unit warning only. Seen most often in summer during hot water. First check: check the setting of the related parameter. Typical values when it appears: supply voltage above 21. Part usually needed: VP-10337. Time allowed under warranty: 45 minutes.

**F262 Controller board: over-temperature.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature above 110. Part usually needed: VP-10158. Time allowed under warranty: 90 minutes.

**F263 Outdoor air sensor: phase missing.** The unit warning only. Seen most often after work on the water side. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature below 1.2. Part usually needed: VP-13895. Time allowed under warranty: 45 minutes.

**F264 Controller board: flow too low.** The unit resets itself. Seen most often in the first weeks after commissioning. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature below 0.8. Part usually needed: VP-14772. Time allowed under warranty: 60 minutes.

**F265 Crankcase heater: pressure too high.** The unit resets itself after 10 minutes. Seen most often in frost. First check: replace the part. Typical values when it appears: suction pressure above 0.8. Part usually needed: VP-11636. Time allowed under warranty: 60 minutes.

**F266 Condensate heater: checksum error.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature above 0.8. Part usually needed: VP-10152. Time allowed under warranty: 90 minutes.

**F267 Mixing valve: value outside the plausible range.** The unit locks the unit until reset by service. Seen most often in frost. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature above 110. Part usually needed: VP-12035. Time allowed under warranty: 20 minutes.

**F268 High pressure switch: limit not reached in time.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: clean the strainer and bleed the circuit. Typical values when it appears: supply voltage below 1.2. Part usually needed: VP-15940. Time allowed under warranty: 30 minutes.

**F269 Circulation pump: over-current.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: let the unit cool down and check the air path. Typical values when it appears: return temperature above 18. Part usually needed: VP-11483. Time allowed under warranty: 30 minutes.

**F270 Expansion valve: configuration mismatch.** The unit resets itself. Seen most often after work on the water side. First check: measure the resistance against the sensor table. Typical values when it appears: supply voltage below 0.8. Part usually needed: VP-14730. Time allowed under warranty: 90 minutes.

**F271 Low pressure transducer: checksum error.** The unit switches to backup heating. Seen most often in cascades. First check: replace the part. Typical values when it appears: return temperature above 360. Part usually needed: VP-14077. Time allowed under warranty: 60 minutes.

**F272 Circulation pump: pressure too low.** The unit warning only. Seen most often in the first weeks after commissioning. First check: clean the strainer and bleed the circuit. Typical values when it appears: supply voltage below 1.2. Part usually needed: VP-12023. Time allowed under warranty: 30 minutes.

**F273 High pressure switch: value outside the plausible range.** The unit warning only. Seen most often in frost. First check: measure the resistance against the sensor table. Typical values when it appears: flow above 110. Part usually needed: VP-15602. Time allowed under warranty: 20 minutes.

**F274 Inverter: sensor short circuit.** The unit warning only. Seen most often in frost. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: return temperature above 3. Part usually needed: VP-15672. Time allowed under warranty: 60 minutes.

**F275 Inverter: no communication.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: clean the strainer and bleed the circuit. Typical values when it appears: supply voltage below 3. Part usually needed: VP-15296. Time allowed under warranty: 90 minutes.

**F276 Diverter valve: phase missing.** The unit locks the unit until reset at the controller. Seen most often in cascades. First check: check the supply and the fuses. Typical values when it appears: suction pressure below 21. Part usually needed: VP-15516. Time allowed under warranty: 45 minutes.

**F277 Circulation pump: over-current.** The unit switches to backup heating. Seen most often in cascades. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure above 2.5. Part usually needed: VP-10920. Time allowed under warranty: 90 minutes.

**F278 Return sensor: pressure too high.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature above 360. Part usually needed: VP-16263. Time allowed under warranty: 45 minutes.

**F279 Four-way valve: contact did not open.** The unit warning only. Seen most often in cascades. First check: update the firmware. Typical values when it appears: flow above 3. Part usually needed: VP-12584. Time allowed under warranty: 60 minutes.

**F280 Flow meter: value outside the plausible range.** The unit warning only. Seen most often in frost. First check: measure the resistance against the sensor table. Typical values when it appears: flow below 18. Part usually needed: VP-13491. Time allowed under warranty: 20 minutes.

**F281 High pressure switch: sensor open circuit.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: measure the resistance against the sensor table. Typical values when it appears: suction pressure above 440. Part usually needed: VP-14290. Time allowed under warranty: 45 minutes.

**F282 Mixing valve: pressure too high.** The unit warning only. Seen most often after work on the water side. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature below 18. Part usually needed: VP-11326. Time allowed under warranty: 20 minutes.

**F283 Inverter: sensor open circuit.** The unit resets itself after 10 minutes. Seen most often in frost. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature below 440. Part usually needed: VP-12411. Time allowed under warranty: 20 minutes.

**F284 Discharge gas sensor: flow too low.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature above 110. Part usually needed: VP-14798. Time allowed under warranty: 20 minutes.

**F285 Return sensor: configuration mismatch.** The unit warning only. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: discharge temperature below 2.5. Part usually needed: VP-11850. Time allowed under warranty: 90 minutes.

**F286 Diverter valve: no communication.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: update the firmware. Typical values when it appears: supply voltage above 0.8. Part usually needed: VP-10559. Time allowed under warranty: 20 minutes.

**F287 Flow sensor: checksum error.** The unit resets itself. Seen most often after a power cut. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: flow above 3. Part usually needed: VP-13151. Time allowed under warranty: 30 minutes.

**F288 Buffer sensor: configuration mismatch.** The unit resets itself after 10 minutes. Seen most often after a power cut. First check: check the plug and the cable, then replace the part. Typical values when it appears: suction pressure above 95. Part usually needed: VP-15533. Time allowed under warranty: 20 minutes.

**F289 Hot water tank sensor: sensor open circuit.** The unit resets itself. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: discharge temperature below 110. Part usually needed: VP-11553. Time allowed under warranty: 90 minutes.

**F290 High pressure switch: flow too low.** The unit resets itself. Seen most often in summer during hot water. First check: replace the part. Typical values when it appears: return temperature above 0.8. Part usually needed: VP-11809. Time allowed under warranty: 30 minutes.

**F291 Flow meter: sensor short circuit.** The unit resets itself after 10 minutes. Seen most often in the first weeks after commissioning. First check: update the firmware. Typical values when it appears: suction pressure above 18. Part usually needed: VP-14902. Time allowed under warranty: 20 minutes.

**F292 Crankcase heater: pressure too low.** The unit warning only. Seen most often after a power cut. First check: let the unit cool down and check the air path. Typical values when it appears: suction pressure below 18. Part usually needed: VP-10269. Time allowed under warranty: 30 minutes.

**F293 Compressor: limit exceeded.** The unit resets itself. Seen most often in the first weeks after commissioning. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature above 18. Part usually needed: VP-10178. Time allowed under warranty: 30 minutes.

**F294 Fan 2: over-temperature.** The unit switches to backup heating. Seen most often in summer during hot water. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature below 1.2. Part usually needed: VP-15540. Time allowed under warranty: 45 minutes.

**F295 Outdoor air sensor: configuration mismatch.** The unit locks the unit until reset by service. Seen most often in the first weeks after commissioning. First check: check the supply and the fuses. Typical values when it appears: flow below 0.8. Part usually needed: VP-15149. Time allowed under warranty: 20 minutes.

**F296 Fan 1: flow too low.** The unit resets itself. Seen most often in frost. First check: measure the resistance against the sensor table. Typical values when it appears: supply voltage above 3. Part usually needed: VP-11162. Time allowed under warranty: 20 minutes.

**F297 Expansion valve: limit exceeded.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: replace the part. Typical values when it appears: supply voltage above 21. Part usually needed: VP-10781. Time allowed under warranty: 45 minutes.

**F298 Backup heater: sensor open circuit.** The unit locks the unit until reset by service. Seen most often in frost. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure below 3. Part usually needed: VP-12123. Time allowed under warranty: 20 minutes.

**F299 Four-way valve: sensor short circuit.** The unit warning only. Seen most often after a power cut. First check: check the supply and the fuses. Typical values when it appears: discharge temperature above 95. Part usually needed: VP-12873. Time allowed under warranty: 20 minutes.

**F300 Diverter valve: pressure too low.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: update the firmware. Typical values when it appears: flow below 110. Part usually needed: VP-15309. Time allowed under warranty: 20 minutes.

**F302 Flow sensor: contact did not open.** The unit locks the unit until reset by service. Seen most often in the first weeks after commissioning. First check: check the supply and the fuses. Typical values when it appears: flow below 360. Part usually needed: VP-13143. Time allowed under warranty: 20 minutes.

**F303 Backup heater: contact did not open.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: let the unit cool down and check the air path. Typical values when it appears: return temperature above 3. Part usually needed: VP-14086. Time allowed under warranty: 45 minutes.

**F304 Flow sensor: over-temperature.** The unit locks the unit until reset by service. Seen most often after work on the water side. First check: update the firmware. Typical values when it appears: discharge temperature above 18. Part usually needed: VP-14185. Time allowed under warranty: 45 minutes.

**F305 Expansion valve: pressure too high.** The unit locks the unit until reset at the controller. Seen most often after a power cut. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature below 1.2. Part usually needed: VP-14818. Time allowed under warranty: 45 minutes.

**F306 Circulation pump: limit exceeded.** The unit resets itself. Seen most often after work on the water side. First check: update the firmware. Typical values when it appears: discharge temperature above 95. Part usually needed: VP-11557. Time allowed under warranty: 90 minutes.

**F307 Outdoor air sensor: no communication.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: check the plug and the cable, then replace the part. Typical values when it appears: return temperature below 360. Part usually needed: VP-15665. Time allowed under warranty: 20 minutes.

**F308 Mixing valve: over-current.** The unit locks the unit until reset by service. Seen most often after work on the water side. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature above 2.5. Part usually needed: VP-13078. Time allowed under warranty: 60 minutes.

**F309 Condensate heater: flow too low.** The unit locks the unit until reset by service. Seen most often on units older than 5 years. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature above 1.2. Part usually needed: VP-13234. Time allowed under warranty: 30 minutes.

**F310 Fan 1: configuration mismatch.** The unit resets itself after 10 minutes. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: supply voltage below 440. Part usually needed: VP-14908. Time allowed under warranty: 30 minutes.

**F311 Crankcase heater: limit not reached in time.** The unit warning only. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure below 440. Part usually needed: VP-10248. Time allowed under warranty: 90 minutes.

**F312 Low pressure transducer: sensor short circuit.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure below 1.2. Part usually needed: VP-11251. Time allowed under warranty: 60 minutes.

**F313 Four-way valve: flow too low.** The unit resets itself. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: flow below 18. Part usually needed: VP-10908. Time allowed under warranty: 45 minutes.

**F314 Mixing valve: no communication.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: discharge temperature below 360. Part usually needed: VP-11269. Time allowed under warranty: 45 minutes.

**F315 High pressure switch: no communication.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature above 440. Part usually needed: VP-11982. Time allowed under warranty: 20 minutes.

**F316 Backup heater: no communication.** The unit locks the unit until reset by service. Seen most often on units older than 5 years. First check: update the firmware. Typical values when it appears: suction pressure above 110. Part usually needed: VP-13600. Time allowed under warranty: 30 minutes.

**F317 Suction gas sensor: over-temperature.** The unit warning only. Seen most often in frost. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: discharge temperature below 21. Part usually needed: VP-11901. Time allowed under warranty: 20 minutes.

**F318 Backup heater: pressure too high.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: check the plug and the cable, then replace the part. Typical values when it appears: flow above 110. Part usually needed: VP-12521. Time allowed under warranty: 20 minutes.

**F319 Hot water tank sensor: contact did not close.** The unit warning only. Seen most often in the first weeks after commissioning. First check: check the supply and the fuses. Typical values when it appears: supply voltage above 110. Part usually needed: VP-15130. Time allowed under warranty: 60 minutes.

**F320 Diverter valve: no communication.** The unit switches to backup heating. Seen most often in cascades. First check: check the setting of the related parameter. Typical values when it appears: return temperature above 3. Part usually needed: VP-10075. Time allowed under warranty: 30 minutes.

**F321 Return sensor: flow too low.** The unit warning only. Seen most often in cascades. First check: check the supply and the fuses. Typical values when it appears: suction pressure above 95. Part usually needed: VP-11072. Time allowed under warranty: 30 minutes.

**F322 Outdoor air sensor: sensor open circuit.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: supply voltage above 440. Part usually needed: VP-10523. Time allowed under warranty: 45 minutes.

**F323 Four-way valve: sensor open circuit.** The unit resets itself. Seen most often after work on the water side. First check: measure the resistance against the sensor table. Typical values when it appears: suction pressure below 440. Part usually needed: VP-14265. Time allowed under warranty: 60 minutes.

**F324 Flow sensor: contact did not open.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: let the unit cool down and check the air path. Typical values when it appears: supply voltage below 1.2. Part usually needed: VP-13347. Time allowed under warranty: 30 minutes.

**F325 Inverter: checksum error.** The unit resets itself after 10 minutes. Seen most often after a power cut. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure above 2.5. Part usually needed: VP-11592. Time allowed under warranty: 60 minutes.

**F326 High pressure switch: pressure too low.** The unit warning only. Seen most often after a power cut. First check: replace the part. Typical values when it appears: supply voltage below 2.5. Part usually needed: VP-11070. Time allowed under warranty: 45 minutes.

**F327 Expansion valve: pressure too low.** The unit switches to backup heating. Seen most often in summer during hot water. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure below 21. Part usually needed: VP-10025. Time allowed under warranty: 20 minutes.

**F328 Compressor: no communication.** The unit switches to backup heating. Seen most often after a power cut. First check: replace the part. Typical values when it appears: supply voltage below 95. Part usually needed: VP-10570. Time allowed under warranty: 20 minutes.

**F329 Inverter: over-current.** The unit resets itself after 10 minutes. Seen most often in the first weeks after commissioning. First check: replace the part. Typical values when it appears: supply voltage above 18. Part usually needed: VP-10793. Time allowed under warranty: 45 minutes.

**F330 Discharge gas sensor: value outside the plausible range.** The unit locks the unit until reset by service. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: discharge temperature above 3. Part usually needed: VP-10396. Time allowed under warranty: 60 minutes.

**F331 Mixing valve: flow too low.** The unit switches to backup heating. Seen most often in frost. First check: update the firmware. Typical values when it appears: supply voltage below 95. Part usually needed: VP-14118. Time allowed under warranty: 20 minutes.

**F332 Compressor: limit exceeded.** The unit warning only. Seen most often in the first weeks after commissioning. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: discharge temperature below 21. Part usually needed: VP-13113. Time allowed under warranty: 20 minutes.

**F333 High pressure switch: sensor open circuit.** The unit locks the unit until reset at the controller. Seen most often after work on the water side. First check: measure the resistance against the sensor table. Typical values when it appears: return temperature below 0.8. Part usually needed: VP-13811. Time allowed under warranty: 20 minutes.

**F334 Mixing valve: phase missing.** The unit switches to backup heating. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure above 18. Part usually needed: VP-13838. Time allowed under warranty: 45 minutes.

**F335 High pressure switch: no communication.** The unit resets itself after 10 minutes. Seen most often in the first weeks after commissioning. First check: check the supply and the fuses. Typical values when it appears: discharge temperature below 18. Part usually needed: VP-10673. Time allowed under warranty: 60 minutes.

**F336 Circulation pump: pressure too low.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: check the setting of the related parameter. Typical values when it appears: flow above 18. Part usually needed: VP-12381. Time allowed under warranty: 60 minutes.

**F337 Flow sensor: over-temperature.** The unit locks the unit until reset at the controller. Seen most often on units older than 5 years. First check: clean the strainer and bleed the circuit. Typical values when it appears: suction pressure below 110. Part usually needed: VP-11477. Time allowed under warranty: 30 minutes.

**F338 Buffer sensor: pressure too high.** The unit resets itself. Seen most often in the first weeks after commissioning. First check: update the firmware. Typical values when it appears: suction pressure below 440. Part usually needed: VP-15561. Time allowed under warranty: 90 minutes.

**F339 Backup heater: pressure too high.** The unit locks the unit until reset by service. Seen most often in the first weeks after commissioning. First check: check the setting of the related parameter. Typical values when it appears: return temperature below 18. Part usually needed: VP-16034. Time allowed under warranty: 45 minutes.

**F340 Circulation pump: value outside the plausible range.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: measure the resistance against the sensor table. Typical values when it appears: flow below 360. Part usually needed: VP-12311. Time allowed under warranty: 90 minutes.

**F341 Flow sensor: pressure too high.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: let the unit cool down and check the air path. Typical values when it appears: return temperature below 3. Part usually needed: VP-11389. Time allowed under warranty: 90 minutes.

**F342 Controller board: checksum error.** The unit resets itself. Seen most often after a power cut. First check: check the supply and the fuses. Typical values when it appears: return temperature below 95. Part usually needed: VP-11670. Time allowed under warranty: 60 minutes.

**F343 Fan 2: flow too low.** The unit warning only. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: suction pressure above 110. Part usually needed: VP-15913. Time allowed under warranty: 20 minutes.

**F344 Inverter: contact did not close.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: discharge temperature below 110. Part usually needed: VP-11389. Time allowed under warranty: 30 minutes.

**F345 Fan 1: contact did not close.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: let the unit cool down and check the air path. Typical values when it appears: flow below 1.2. Part usually needed: VP-11616. Time allowed under warranty: 20 minutes.

**F346 Discharge gas sensor: value outside the plausible range.** The unit resets itself. Seen most often in summer during hot water. First check: replace the part. Typical values when it appears: flow below 1.2. Part usually needed: VP-12902. Time allowed under warranty: 60 minutes.

**F347 Flow meter: contact did not open.** The unit resets itself after 10 minutes. Seen most often in frost. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature below 360. Part usually needed: VP-13562. Time allowed under warranty: 20 minutes.

**F348 Controller board: contact did not open.** The unit switches to backup heating. Seen most often in summer during hot water. First check: restart the controller; if it returns, call service. Typical values when it appears: return temperature above 2.5. Part usually needed: VP-13184. Time allowed under warranty: 60 minutes.

**F349 Suction gas sensor: phase missing.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: clean the strainer and bleed the circuit. Typical values when it appears: flow below 440. Part usually needed: VP-11858. Time allowed under warranty: 90 minutes.

**F350 Fan 2: contact did not close.** The unit warning only. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature above 360. Part usually needed: VP-11780. Time allowed under warranty: 20 minutes.

**F351 Controller board: configuration mismatch.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: restart the controller; if it returns, call service. Typical values when it appears: return temperature below 3. Part usually needed: VP-13984. Time allowed under warranty: 20 minutes.

**F352 Circulation pump: checksum error.** The unit resets itself. Seen most often in the first weeks after commissioning. First check: let the unit cool down and check the air path. Typical values when it appears: suction pressure above 18. Part usually needed: VP-12884. Time allowed under warranty: 90 minutes.

**F353 Return sensor: limit exceeded.** The unit switches to backup heating. Seen most often in cascades. First check: measure the resistance against the sensor table. Typical values when it appears: suction pressure above 2.5. Part usually needed: VP-10322. Time allowed under warranty: 30 minutes.

**F354 Discharge gas sensor: pressure too low.** The unit locks the unit until reset by service. Seen most often in frost. First check: check the setting of the related parameter. Typical values when it appears: suction pressure above 2.5. Part usually needed: VP-13305. Time allowed under warranty: 20 minutes.

**F355 Return sensor: limit not reached in time.** The unit locks the unit until reset by service. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: flow below 3. Part usually needed: VP-13190. Time allowed under warranty: 30 minutes.

**F356 Discharge gas sensor: pressure too high.** The unit locks the unit until reset at the controller. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: flow below 360. Part usually needed: VP-13368. Time allowed under warranty: 90 minutes.

**F357 Return sensor: configuration mismatch.** The unit switches to backup heating. Seen most often in frost. First check: check the setting of the related parameter. Typical values when it appears: suction pressure above 18. Part usually needed: VP-15658. Time allowed under warranty: 60 minutes.

**F358 Inverter: over-current.** The unit resets itself. Seen most often after work on the water side. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure above 95. Part usually needed: VP-14285. Time allowed under warranty: 30 minutes.

**F359 Discharge gas sensor: contact did not open.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: restart the controller; if it returns, call service. Typical values when it appears: flow above 110. Part usually needed: VP-16047. Time allowed under warranty: 20 minutes.

**F360 Circulation pump: sensor short circuit.** The unit locks the unit until reset by service. Seen most often in frost. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: flow below 360. Part usually needed: VP-15200. Time allowed under warranty: 45 minutes.

**F361 Four-way valve: value outside the plausible range.** The unit resets itself. Seen most often in summer during hot water. First check: update the firmware. Typical values when it appears: discharge temperature below 2.5. Part usually needed: VP-15897. Time allowed under warranty: 45 minutes.

**F362 Hot water tank sensor: contact did not open.** The unit switches to backup heating. Seen most often in cascades. First check: check the plug and the cable, then replace the part. Typical values when it appears: suction pressure below 0.8. Part usually needed: VP-14274. Time allowed under warranty: 60 minutes.

**F363 Bus module: contact did not close.** The unit resets itself. Seen most often on units older than 5 years. First check: check the supply and the fuses. Typical values when it appears: discharge temperature below 110. Part usually needed: VP-14594. Time allowed under warranty: 90 minutes.

**F364 Backup heater: checksum error.** The unit resets itself. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: flow above 0.8. Part usually needed: VP-12531. Time allowed under warranty: 30 minutes.

**F365 Low pressure transducer: pressure too high.** The unit switches to backup heating. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: discharge temperature above 1.2. Part usually needed: VP-15971. Time allowed under warranty: 60 minutes.

**F366 Suction gas sensor: phase missing.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: restart the controller; if it returns, call service. Typical values when it appears: supply voltage below 110. Part usually needed: VP-11801. Time allowed under warranty: 90 minutes.

**F367 Four-way valve: limit exceeded.** The unit resets itself. Seen most often in cascades. First check: update the firmware. Typical values when it appears: discharge temperature below 2.5. Part usually needed: VP-12319. Time allowed under warranty: 20 minutes.

**F368 Inverter: limit not reached in time.** The unit locks the unit until reset by service. Seen most often in cascades. First check: check the supply and the fuses. Typical values when it appears: flow below 18. Part usually needed: VP-15454. Time allowed under warranty: 90 minutes.

**F369 Expansion valve: sensor open circuit.** The unit locks the unit until reset at the controller. Seen most often after work on the water side. First check: update the firmware. Typical values when it appears: flow below 18. Part usually needed: VP-11831. Time allowed under warranty: 20 minutes.

**F370 Diverter valve: pressure too high.** The unit locks the unit until reset at the controller. Seen most often on units older than 5 years. First check: update the firmware. Typical values when it appears: discharge temperature above 2.5. Part usually needed: VP-13931. Time allowed under warranty: 60 minutes.

**F371 Low pressure transducer: over-temperature.** The unit resets itself. Seen most often in frost. First check: clean the strainer and bleed the circuit. Typical values when it appears: suction pressure below 360. Part usually needed: VP-12034. Time allowed under warranty: 20 minutes.

**F372 High pressure switch: limit not reached in time.** The unit switches to backup heating. Seen most often in frost. First check: check the setting of the related parameter. Typical values when it appears: flow below 360. Part usually needed: VP-14766. Time allowed under warranty: 45 minutes.

**F373 Condensate heater: pressure too low.** The unit resets itself after 10 minutes. Seen most often in the first weeks after commissioning. First check: restart the controller; if it returns, call service. Typical values when it appears: flow above 0.8. Part usually needed: VP-14675. Time allowed under warranty: 30 minutes.

**F374 Controller board: contact did not close.** The unit switches to backup heating. Seen most often in summer during hot water. First check: replace the part. Typical values when it appears: flow above 110. Part usually needed: VP-11754. Time allowed under warranty: 20 minutes.

**F375 Crankcase heater: pressure too high.** The unit warning only. Seen most often in the first weeks after commissioning. First check: check the plug and the cable, then replace the part. Typical values when it appears: flow below 95. Part usually needed: VP-11704. Time allowed under warranty: 90 minutes.

**F376 Circulation pump: pressure too high.** The unit warning only. Seen most often in cascades. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure below 440. Part usually needed: VP-13355. Time allowed under warranty: 60 minutes.

**F377 Buffer sensor: flow too low.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: supply voltage below 18. Part usually needed: VP-15320. Time allowed under warranty: 90 minutes.

**F378 Fan 2: over-current.** The unit warning only. Seen most often after a power cut. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature above 95. Part usually needed: VP-12443. Time allowed under warranty: 45 minutes.

**F379 Expansion valve: checksum error.** The unit warning only. Seen most often on units older than 5 years. First check: update the firmware. Typical values when it appears: suction pressure below 18. Part usually needed: VP-12503. Time allowed under warranty: 20 minutes.

**F380 Crankcase heater: phase missing.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: discharge temperature above 110. Part usually needed: VP-14679. Time allowed under warranty: 90 minutes.

**F381 Inverter: over-current.** The unit locks the unit until reset by service. Seen most often in the first weeks after commissioning. First check: measure the resistance against the sensor table. Typical values when it appears: supply voltage below 1.2. Part usually needed: VP-11023. Time allowed under warranty: 90 minutes.

**F382 Four-way valve: limit exceeded.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: suction pressure above 0.8. Part usually needed: VP-13138. Time allowed under warranty: 30 minutes.

**F383 Bus module: flow too low.** The unit switches to backup heating. Seen most often in summer during hot water. First check: update the firmware. Typical values when it appears: suction pressure above 440. Part usually needed: VP-13325. Time allowed under warranty: 30 minutes.

**F384 High pressure switch: configuration mismatch.** The unit resets itself. Seen most often after work on the water side. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: discharge temperature below 18. Part usually needed: VP-10478. Time allowed under warranty: 60 minutes.

**F385 Outdoor air sensor: phase missing.** The unit warning only. Seen most often in frost. First check: let the unit cool down and check the air path. Typical values when it appears: flow above 0.8. Part usually needed: VP-14640. Time allowed under warranty: 45 minutes.

**F386 Crankcase heater: value outside the plausible range.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: clean the strainer and bleed the circuit. Typical values when it appears: return temperature above 21. Part usually needed: VP-10475. Time allowed under warranty: 60 minutes.

**F387 Low pressure transducer: contact did not close.** The unit switches to backup heating. Seen most often in frost. First check: update the firmware. Typical values when it appears: supply voltage above 0.8. Part usually needed: VP-13073. Time allowed under warranty: 90 minutes.

**F388 Compressor: limit not reached in time.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: measure the resistance against the sensor table. Typical values when it appears: discharge temperature above 2.5. Part usually needed: VP-10700. Time allowed under warranty: 30 minutes.

**F389 Backup heater: no communication.** The unit locks the unit until reset by service. Seen most often in frost. First check: update the firmware. Typical values when it appears: return temperature above 1.2. Part usually needed: VP-14514. Time allowed under warranty: 45 minutes.

**F390 Flow meter: sensor open circuit.** The unit warning only. Seen most often after a power cut. First check: let the unit cool down and check the air path. Typical values when it appears: supply voltage below 0.8. Part usually needed: VP-10342. Time allowed under warranty: 90 minutes.

**F391 Compressor: flow too low.** The unit warning only. Seen most often in cascades. First check: update the firmware. Typical values when it appears: return temperature above 95. Part usually needed: VP-14964. Time allowed under warranty: 30 minutes.

**F392 Mixing valve: phase missing.** The unit resets itself. Seen most often after work on the water side. First check: restart the controller; if it returns, call service. Typical values when it appears: suction pressure below 3. Part usually needed: VP-12817. Time allowed under warranty: 60 minutes.

**F393 Diverter valve: contact did not close.** The unit resets itself after 10 minutes. Seen most often in frost. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: flow above 0.8. Part usually needed: VP-13994. Time allowed under warranty: 30 minutes.

**F394 Discharge gas sensor: sensor short circuit.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: update the firmware. Typical values when it appears: flow above 440. Part usually needed: VP-15813. Time allowed under warranty: 45 minutes.

**F395 Outdoor air sensor: pressure too low.** The unit locks the unit until reset by service. Seen most often in summer during hot water. First check: update the firmware. Typical values when it appears: supply voltage above 360. Part usually needed: VP-11203. Time allowed under warranty: 60 minutes.

**F396 Mixing valve: sensor open circuit.** The unit resets itself after 10 minutes. Seen most often after work on the water side. First check: check the plug and the cable, then replace the part. Typical values when it appears: suction pressure above 95. Part usually needed: VP-14123. Time allowed under warranty: 45 minutes.

**F397 Buffer sensor: flow too low.** The unit locks the unit until reset by service. Seen most often after work on the water side. First check: check the plug and the cable, then replace the part. Typical values when it appears: suction pressure below 360. Part usually needed: VP-12417. Time allowed under warranty: 60 minutes.

**F398 Discharge gas sensor: value outside the plausible range.** The unit resets itself. Seen most often in summer during hot water. First check: restart the controller; if it returns, call service. Typical values when it appears: flow below 440. Part usually needed: VP-14450. Time allowed under warranty: 90 minutes.

**F399 Suction gas sensor: over-current.** The unit resets itself after 10 minutes. Seen most often after work on the water side. First check: update the firmware. Typical values when it appears: discharge temperature above 95. Part usually needed: VP-11435. Time allowed under warranty: 90 minutes.

**F400 Inverter: limit not reached in time.** The unit resets itself. Seen most often in the first weeks after commissioning. First check: let the unit cool down and check the air path. Typical values when it appears: flow below 95. Part usually needed: VP-11811. Time allowed under warranty: 90 minutes.

**F401 Buffer sensor: sensor short circuit.** The unit locks the unit until reset at the controller. Seen most often in summer during hot water. First check: clean the strainer and bleed the circuit. Typical values when it appears: flow above 21. Part usually needed: VP-12038. Time allowed under warranty: 45 minutes.

**F402 Discharge gas sensor: over-current.** The unit resets itself. Seen most often in the first weeks after commissioning. First check: check the setting of the related parameter. Typical values when it appears: flow below 110. Part usually needed: VP-14279. Time allowed under warranty: 45 minutes.

**F403 Fan 1: flow too low.** The unit warning only. Seen most often on units older than 5 years. First check: check the setting of the related parameter. Typical values when it appears: flow below 0.8. Part usually needed: VP-12587. Time allowed under warranty: 45 minutes.

**F404 Bus module: pressure too high.** The unit resets itself after 10 minutes. Seen most often on units older than 5 years. First check: check the plug and the cable, then replace the part. Typical values when it appears: supply voltage below 360. Part usually needed: VP-13404. Time allowed under warranty: 90 minutes.

**F405 Return sensor: phase missing.** The unit switches to backup heating. Seen most often in frost. First check: check the supply and the fuses. Typical values when it appears: flow above 0.8. Part usually needed: VP-11170. Time allowed under warranty: 30 minutes.

**F406 Outdoor air sensor: pressure too low.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: check the setting of the related parameter. Typical values when it appears: return temperature above 110. Part usually needed: VP-15397. Time allowed under warranty: 90 minutes.

**F407 Hot water tank sensor: no communication.** The unit locks the unit until reset at the controller. Seen most often after work on the water side. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: suction pressure above 1.2. Part usually needed: VP-10043. Time allowed under warranty: 60 minutes.

**F408 Buffer sensor: over-temperature.** The unit resets itself after 10 minutes. Seen most often in the first weeks after commissioning. First check: check the supply and the fuses. Typical values when it appears: return temperature below 21. Part usually needed: VP-11770. Time allowed under warranty: 60 minutes.

**F409 Suction gas sensor: over-temperature.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: replace the part. Typical values when it appears: return temperature above 2.5. Part usually needed: VP-15927. Time allowed under warranty: 45 minutes.

**F410 Diverter valve: contact did not open.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: let the unit cool down and check the air path. Typical values when it appears: flow above 110. Part usually needed: VP-11826. Time allowed under warranty: 20 minutes.

**F411 Return sensor: over-current.** The unit warning only. Seen most often in summer during hot water. First check: measure the resistance against the sensor table. Typical values when it appears: flow below 95. Part usually needed: VP-11281. Time allowed under warranty: 30 minutes.

**F412 Buffer sensor: configuration mismatch.** The unit warning only. Seen most often in summer during hot water. First check: let the unit cool down and check the air path. Typical values when it appears: suction pressure below 110. Part usually needed: VP-10923. Time allowed under warranty: 45 minutes.

**F413 Outdoor air sensor: pressure too low.** The unit switches to backup heating. Seen most often in the first weeks after commissioning. First check: check the setting of the related parameter. Typical values when it appears: return temperature above 3. Part usually needed: VP-10634. Time allowed under warranty: 20 minutes.

**F414 Controller board: contact did not close.** The unit resets itself after 10 minutes. Seen most often in cascades. First check: check the setting of the related parameter. Typical values when it appears: flow above 110. Part usually needed: VP-12696. Time allowed under warranty: 20 minutes.

**F415 Hot water tank sensor: sensor open circuit.** The unit resets itself. Seen most often on units older than 5 years. First check: check the plug and the cable, then replace the part. Typical values when it appears: suction pressure below 440. Part usually needed: VP-10792. Time allowed under warranty: 60 minutes.

**F416 Hot water tank sensor: pressure too high.** The unit warning only. Seen most often on units older than 5 years. First check: check the refrigerant circuit for leaks (certified staff only). Typical values when it appears: discharge temperature below 95. Part usually needed: VP-14228. Time allowed under warranty: 60 minutes.

**F417 Crankcase heater: sensor short circuit.** The unit switches to backup heating. Seen most often in summer during hot water. First check: check the plug and the cable, then replace the part. Typical values when it appears: discharge temperature above 21. Part usually needed: VP-11682. Time allowed under warranty: 45 minutes.

**F418 Flow sensor: over-temperature.** The unit locks the unit until reset by service. Seen most often after a power cut. First check: check the setting of the related parameter. Typical values when it appears: supply voltage above 95. Part usually needed: VP-12311. Time allowed under warranty: 90 minutes.

**F419 Bus module: over-current.** The unit switches to backup heating. Seen most often on units older than 5 years. First check: replace the part. Typical values when it appears: return temperature above 21. Part usually needed: VP-16270. Time allowed under warranty: 60 minutes.

## Resetting

Hold the OK key for 5 seconds on the fault screen. A fault that locks the unit until reset by service needs the service code. Never reset F301 before the cause is found.

**Fault note 1.** Where this document refers to a person, that includes a company, a partnership and any other body with legal personality, and their lawful successors.

**Fault note 2.** Each party will act in good faith and will cooperate reasonably with the other to give effect to the purpose of this document.

**Fault note 3.** We process personal data as described in our privacy notice. We keep records only for as long as we need them for the purposes stated there.

**Fault note 4.** Where an amount is stated including tax, the tax rate in force on the date of the invoice applies, and a change in the rate changes the amount accordingly.

**Fault note 5.** Headings in this document are for convenience only and do not affect its interpretation. Words in the singular include the plural and the other way round.

**Fault note 6.** Copies of earlier versions of this document are kept in the archive and can be requested. They apply only to the period stated on their cover.

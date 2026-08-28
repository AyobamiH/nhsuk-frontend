# Checkbox centring evidence

The score is the mean absolute horizontal distance between the rendered check-mark bounding-box centre and the rendered checkbox-border centre.
Lower is better. Values are normalized to CSS pixels.

| Variant | Mean absolute error | Maximum absolute error | Samples |
| --- | ---: | ---: | ---: |
| candidate-rem-minus-0.03125 | 0.0417px | 0.2500px | 12 |
| legacy-pre-v10.6 | 0.0667px | 0.4000px | 12 |
| fixed-minus-0.5px | 0.2083px | 0.7500px | 12 |
| fixed-minus-0.75px | 0.2750px | 0.5000px | 12 |
| fixed-minus-0.25px | 0.4972px | 1.0000px | 12 |
| current | 0.7194px | 1.2500px | 12 |

Candidate result: **PASS**

The WebKit result is an approximation of Safari. DPR values are browser-context emulation on the named operating system, not proof of physical monitor scaling.
The 200% text-size scenario changes the root font size from 16px to 32px so the rem-based correction is evaluated under text resizing.
Forced-colours screenshots and computed-style records verify that the selected mark remains rendered.

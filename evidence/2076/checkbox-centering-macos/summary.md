# Checkbox centring evidence

The score is the mean absolute horizontal distance between the rendered check-mark bounding-box centre and the rendered checkbox-border centre.
Lower is better. Values are normalized to CSS pixels.

| Variant | Mean absolute error | Maximum absolute error | Samples |
| --- | ---: | ---: | ---: |
| legacy-pre-v10.6 | 0.0611px | 0.4000px | 12 |
| candidate-rem-minus-0.03125 | 0.1028px | 0.4000px | 12 |
| fixed-minus-0.5px | 0.2694px | 0.7500px | 12 |
| fixed-minus-0.75px | 0.3083px | 0.8000px | 12 |
| fixed-minus-0.25px | 0.4917px | 1.0000px | 12 |
| current | 0.6861px | 1.2500px | 12 |

Candidate result: **FAIL**

The WebKit result is an approximation of Safari. DPR values are browser-context emulation on the named operating system, not proof of physical monitor scaling.
The 200% text-size scenario changes the root font size from 16px to 32px so the rem-based correction is evaluated under text resizing.
Forced-colours screenshots and computed-style records verify that the selected mark remains rendered.

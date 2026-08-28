import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw


evidence_dir = Path(os.environ["EVIDENCE_DIR"])
records = json.loads((evidence_dir / "records.json").read_text())
forced_states = json.loads((evidence_dir / "forced-colours.json").read_text())


def matching_pixels(image, predicate):
    return [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if predicate(*image.getpixel((x, y)))
    ]


def bounds(points):
    if not points:
        raise RuntimeError("Expected pixels were not found")
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points),
        max(y for _, y in points),
    )


def centre(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


metrics = []
images = {}
for record in records:
    image = Image.open(evidence_dir / record["filename"]).convert("RGB")
    images[
        (
            record["browser"],
            record["scenario"],
            record["deviceScaleFactor"],
            record["variant"],
        )
    ] = image
    red_box = bounds(
        matching_pixels(image, lambda red, green, blue: red > 180 and green < 120 and blue < 120)
    )
    checkbox_box = bounds(
        matching_pixels(image, lambda red, green, blue: red < 80 and green < 100 and blue < 120)
    )
    red_centre = centre(red_box)
    checkbox_centre = centre(checkbox_box)
    factor = record["deviceScaleFactor"]
    metrics.append(
        {
            **record,
            "checkbox_box": checkbox_box,
            "check_mark_box": red_box,
            "horizontal_error_device_pixels": red_centre[0] - checkbox_centre[0],
            "horizontal_error_css_pixels": (red_centre[0] - checkbox_centre[0]) / factor,
            "vertical_error_device_pixels": red_centre[1] - checkbox_centre[1],
            "vertical_error_css_pixels": (red_centre[1] - checkbox_centre[1]) / factor,
        }
    )


by_variant = defaultdict(list)
for metric in metrics:
    by_variant[metric["variant"]].append(metric)

scores = []
for variant, variant_metrics in by_variant.items():
    absolute_errors = [
        abs(metric["horizontal_error_css_pixels"]) for metric in variant_metrics
    ]
    scores.append(
        {
            "variant": variant,
            "mean_absolute_horizontal_error_css_pixels": statistics.mean(absolute_errors),
            "max_absolute_horizontal_error_css_pixels": max(absolute_errors),
            "sample_count": len(absolute_errors),
        }
    )
scores.sort(key=lambda score: score["mean_absolute_horizontal_error_css_pixels"])

score_by_variant = {score["variant"]: score for score in scores}
candidate_name = "candidate-rem-minus-0.03125"
candidate_score = score_by_variant[candidate_name]
current_score = score_by_variant["current"]
best_score = scores[0]

forced_colours_ok = all(
    state["opacity"] == "1"
    and state["borderBottomStyle"] != "none"
    and state["borderLeftStyle"] != "none"
    and float(state["borderBottomWidth"].removesuffix("px")) > 0
    and float(state["borderLeftWidth"].removesuffix("px")) > 0
    and state["transform"] != "none"
    for state in forced_states
)

verdict = {
    "candidate": candidate_name,
    "candidate_is_best_or_tied": (
        candidate_score["mean_absolute_horizontal_error_css_pixels"]
        <= best_score["mean_absolute_horizontal_error_css_pixels"] + 1e-9
    ),
    "candidate_improves_current": (
        candidate_score["mean_absolute_horizontal_error_css_pixels"]
        < current_score["mean_absolute_horizontal_error_css_pixels"]
    ),
    "candidate_max_error_within_half_css_pixel": (
        candidate_score["max_absolute_horizontal_error_css_pixels"] <= 0.5
    ),
    "forced_colours_check_mark_remains_rendered": forced_colours_ok,
    "pass": False,
}
verdict["pass"] = all(
    [
        verdict["candidate_is_best_or_tied"],
        verdict["candidate_improves_current"],
        verdict["candidate_max_error_within_half_css_pixel"],
        verdict["forced_colours_check_mark_remains_rendered"],
    ]
)

(evidence_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
(evidence_dir / "scores.json").write_text(json.dumps(scores, indent=2))
(evidence_dir / "verdict.json").write_text(json.dumps(verdict, indent=2))

summary = [
    "# Checkbox centring evidence",
    "",
    "The score is the mean absolute horizontal distance between the rendered check-mark bounding-box centre and the rendered checkbox-border centre.",
    "Lower is better. Values are normalized to CSS pixels.",
    "",
    "| Variant | Mean absolute error | Maximum absolute error | Samples |",
    "| --- | ---: | ---: | ---: |",
]
for score in scores:
    summary.append(
        f"| {score['variant']} | "
        f"{score['mean_absolute_horizontal_error_css_pixels']:.4f}px | "
        f"{score['max_absolute_horizontal_error_css_pixels']:.4f}px | "
        f"{score['sample_count']} |"
    )
summary.extend(
    [
        "",
        f"Candidate result: **{'PASS' if verdict['pass'] else 'FAIL'}**",
        "",
        "The WebKit result is an approximation of Safari. DPR values are browser-context emulation on the named operating system, not proof of physical monitor scaling.",
        "The 200% text-size scenario changes the root font size from 16px to 32px so the rem-based correction is evaluated under text resizing.",
        "Forced-colours screenshots and computed-style records verify that the selected mark remains rendered.",
        "",
    ]
)
(evidence_dir / "summary.md").write_text("\n".join(summary))


comparison_variants = [
    "legacy-pre-v10.6",
    "current",
    candidate_name,
]
comparison_metrics = [
    metric
    for metric in metrics
    if metric["scenario"] == "default-text"
    and metric["variant"] in comparison_variants
]
comparison_metrics.sort(
    key=lambda metric: (
        metric["browser"],
        metric["deviceScaleFactor"],
        comparison_variants.index(metric["variant"]),
    )
)
rows = sorted(
    {
        (metric["browser"], metric["deviceScaleFactor"])
        for metric in comparison_metrics
    }
)
max_width = max(image.width for image in images.values())
max_height = max(image.height for image in images.values())
cell_width = max_width + 80
cell_height = max_height + 52
canvas = Image.new(
    "RGB", (cell_width * len(comparison_variants), cell_height * len(rows)), "white"
)
draw = ImageDraw.Draw(canvas)
metric_lookup = {
    (metric["browser"], metric["deviceScaleFactor"], metric["variant"]): metric
    for metric in comparison_metrics
}
for row_index, (browser, factor) in enumerate(rows):
    for column, variant in enumerate(comparison_variants):
        metric = metric_lookup[(browser, factor, variant)]
        image = images[(browser, "default-text", factor, variant)]
        x = column * cell_width + 10
        y = row_index * cell_height + 8
        canvas.paste(image, (x, y))
        draw.text((x, y + image.height + 4), f"{browser} DPR {factor}", fill="black")
        draw.text(
            (x, y + image.height + 18),
            f"{variant}: {metric['horizontal_error_css_pixels']:+.3f}px",
            fill="black",
        )
canvas.save(evidence_dir / "comparison.png")

print(json.dumps({"scores": scores, "verdict": verdict}, indent=2))
if not verdict["pass"]:
    raise SystemExit("Candidate did not satisfy the centring acceptance criteria")

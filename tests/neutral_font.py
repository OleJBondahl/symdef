"""A font that measures what no font used to: 0.6 em per character, cap height 0.72 em (D124)."""

from symdef import FontMetrics, Weight

NEUTRAL_FONT = FontMetrics(
    name="Neutral",
    units_per_em=1000,
    cap_height=720,
    ascent=900,
    descent=200,
    advances={Weight.NORMAL: {}, Weight.THICK: {}},
    default_advance={Weight.NORMAL: 600, Weight.THICK: 600},
)

NEUTRAL_FONT_TOML = """
[font]
name = "Neutral"
units_per_em = 1000
cap_height = 720
ascent = 900
descent = 200

[font.default_advance]
normal = 600
thick = 600

[font.advances.normal]

[font.advances.thick]
"""

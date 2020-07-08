import pytest

from colorific import color_names


@pytest.mark.parametrize(
    "hex_codes, expected_names",
    [
        (["000000"], ["black"]),
        (["ffffff"], ["white"]),
        (["ff0000", "00ff00", "0000ff"], ["red", "green", "blue"]),
        (["ffb7c5", "fff8e7"], ["cherry blossom pink", "cosmic latte"]),
        (["c72c49", "ade1af"], ["french raspberry", "celadon"]),
    ],
)
def test_color_names(hex_codes, expected_names):
    names_with_dist = color_names.find_by_hex(hex_codes)
    assert [name.lower() for name, _ in names_with_dist] == expected_names

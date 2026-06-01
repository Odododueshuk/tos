import numpy as np

from core.detector import OrbDetector


def test_classify_orb_returns_confidence():
    detector = OrbDetector()

    orb, confidence = detector.classify_orb(40, 140, 220)

    assert orb == 0
    assert 0.0 <= confidence <= 1.0
    assert confidence >= 0.55


def test_typical_orb_colors_have_usable_confidence():
    detector = OrbDetector()
    samples = [
        (40, 140, 220, 0),
        (220, 70, 60, 1),
        (60, 190, 90, 2),
        (230, 205, 45, 3),
        (145, 70, 180, 4),
        (225, 85, 150, 5),
    ]

    for r, g, b, expected_orb in samples:
        orb, confidence = detector.classify_orb(r, g, b)
        assert orb == expected_orb
        assert confidence >= 0.55


def test_detect_board_returns_confidence_grid():
    detector = OrbDetector()
    image = np.zeros((100, 120, 3), dtype=np.uint8)
    image[:, :, :] = (220, 140, 40)

    grid, obs, confidence = detector.detect_board(image)

    assert len(grid) == 5
    assert len(grid[0]) == 6
    assert len(obs) == 5
    assert len(confidence) == 5
    assert all(0.0 <= value <= 1.0 for row in confidence for value in row)

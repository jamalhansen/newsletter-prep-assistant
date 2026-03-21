"""Tests for newsletter_prep.cta."""

from newsletter_prep.cta import CTAS, get_cta


class TestGetCta:
    def test_issue_1_returns_first_cta(self):
        cta = get_cta(1)
        assert cta.text == CTAS[0]
        assert cta.index == 1

    def test_issue_5_returns_fifth_cta(self):
        cta = get_cta(5)
        assert cta.text == CTAS[4]
        assert cta.index == 5

    def test_wraps_at_length(self):
        cta_6 = get_cta(6)
        cta_1 = get_cta(1)
        assert cta_6.text == cta_1.text

    def test_total_matches_list_length(self):
        cta = get_cta(1)
        assert cta.total == len(CTAS)

    def test_all_ctas_are_nonempty(self):
        for i in range(1, len(CTAS) + 1):
            cta = get_cta(i)
            assert cta.text.strip()

    def test_large_issue_number(self):
        # Should not raise; wraps deterministically
        cta = get_cta(100)
        assert cta.text in CTAS

"""Testes unitarios para o gradiente visual de ciclo de vida (BIT-10).

Cobre `compute_life_color` e `compute_visual_scale` isoladamente, sem
instanciar `Creature`/Pymunk — sao funcoes puras baseadas em age/energy/max_energy.
"""

from simulation.creature import compute_life_color, compute_visual_scale


class TestComputeLifeColor:
    def test_newborn_is_pure_blue(self):
        assert compute_life_color(age=0, energy=100, max_energy=100) == '#3b82f6'

    def test_age_ten_is_pure_green(self):
        assert compute_life_color(age=10, energy=100, max_energy=100) == '#22c55e'

    def test_mature_to_elder_color_changes_continuously_between_ten_and_thirty(self):
        samples = [compute_life_color(age=age, energy=100, max_energy=100) for age in (10, 15, 20, 25, 30)]
        assert len(set(samples)) == len(samples)  # nenhum valor repetido: sempre mudando
        assert samples[0] == '#22c55e'  # ponto de partida inalterado
        assert samples[-1] == '#6b7280'  # termina exatamente onde o ramo ELDER (energia cheia) comeca

    def test_elder_start_full_energy_is_gray(self):
        assert compute_life_color(age=31, energy=100, max_energy=100) == '#6b7280'

    def test_elder_zero_energy_is_near_black(self):
        assert compute_life_color(age=31, energy=0, max_energy=100) == '#111827'

    def test_egg_to_mature_interpolates_between_two_and_ten(self):
        color_at_two = compute_life_color(age=2, energy=100, max_energy=100)
        color_at_six = compute_life_color(age=6, energy=100, max_energy=100)
        color_at_ten = compute_life_color(age=10, energy=100, max_energy=100)
        assert color_at_two == '#3b82f6'
        assert color_at_ten == '#22c55e'
        # ponto intermediario nao deve ser identico a nenhum dos extremos
        assert color_at_six not in ('#3b82f6', '#22c55e')

    def test_elder_interpolates_between_gray_and_black_by_energy_fraction(self):
        color_half_energy = compute_life_color(age=31, energy=50, max_energy=100)
        assert color_half_energy not in ('#6b7280', '#111827')


class TestComputeVisualScale:
    def test_egg_scale_is_point_seven(self):
        assert compute_visual_scale(age=0, energy=100, max_energy=100) == 0.7

    def test_mature_scale_is_one(self):
        assert compute_visual_scale(age=10, energy=100, max_energy=100) == 1.0

    def test_plateau_stays_one_between_ten_and_thirty(self):
        for age in (10, 15, 20, 25, 30):
            assert compute_visual_scale(age=age, energy=100, max_energy=100) == 1.0

    def test_elder_zero_energy_shrinks_to_point_eight_five(self):
        assert compute_visual_scale(age=31, energy=0, max_energy=100) == 0.85

    def test_elder_full_energy_stays_at_one(self):
        assert compute_visual_scale(age=31, energy=100, max_energy=100) == 1.0

    def test_egg_to_mature_scale_grows_monotonically(self):
        scale_at_two = compute_visual_scale(age=2, energy=100, max_energy=100)
        scale_at_six = compute_visual_scale(age=6, energy=100, max_energy=100)
        scale_at_ten = compute_visual_scale(age=10, energy=100, max_energy=100)
        assert scale_at_two == 0.7
        assert scale_at_ten == 1.0
        assert scale_at_two < scale_at_six < scale_at_ten

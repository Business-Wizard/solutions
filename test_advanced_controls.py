"""Test advanced_controls.py."""

import pytest

import advanced_controls
from model import emissionsfactors as ef
import pandas as pd


def test_learning_rate():
    """Test efficiency versus learning rate."""
    ac = advanced_controls.AdvancedControls(
        pds_2014_cost=0, ref_2014_cost=0, conv_2014_cost=0,
        soln_first_cost_efficiency_rate=0.2,
        soln_first_cost_below_conv=True,
        conv_first_cost_efficiency_rate=0.4786)
    assert ac.soln_first_cost_learning_rate == pytest.approx(0.8)
    assert ac.conv_first_cost_learning_rate == pytest.approx(0.5214)
    ac = advanced_controls.AdvancedControls(
        pds_2014_cost=0, ref_2014_cost=0, conv_2014_cost=0,
        soln_first_cost_efficiency_rate=0.33333333,
        soln_first_cost_below_conv=True,
        conv_first_cost_efficiency_rate=1.0)
    assert ac.soln_first_cost_learning_rate == pytest.approx(0.66666667)
    assert ac.conv_first_cost_learning_rate == pytest.approx(0.0)

def test_soln_funit_adoption_2014():
  arg = [['World', 'A', 'B', 'C'], [1, 2, 3, 4]]
  ac = advanced_controls.AdvancedControls(soln_funit_adoption_2014=arg)
  result = ac.soln_funit_adoption_2014
  expected = pd.DataFrame([[1, 2, 3, 4]], columns=['World', 'A', 'B', 'C'], index=[2014])
  expected.index.name = 'Year'
  pd.testing.assert_frame_equal(result, expected)

  ac = advanced_controls.AdvancedControls(soln_funit_adoption_2014=expected)
  result = ac.soln_funit_adoption_2014
  assert result is expected  # should be the same object

def test_electricity_factors():
  soln_energy_efficiency_factor = ""
  conv_annual_energy_used = 2.117
  soln_annual_energy_used = None

  ac = advanced_controls.AdvancedControls(
      soln_energy_efficiency_factor=soln_energy_efficiency_factor,
      conv_annual_energy_used=conv_annual_energy_used,
      soln_annual_energy_used=soln_annual_energy_used)
  assert ac.soln_energy_efficiency_factor == 0
  assert ac.conv_annual_energy_used == pytest.approx(conv_annual_energy_used)
  assert ac.soln_annual_energy_used == 0

def test_lifetimes():
  soln_lifetime_capacity = 50000
  soln_avg_annual_use = 1000
  conv_lifetime_capacity = 10000
  conv_avg_annual_use = 3
  ac = advanced_controls.AdvancedControls(
      soln_lifetime_capacity=soln_lifetime_capacity,
      soln_avg_annual_use=soln_avg_annual_use,
      conv_lifetime_capacity=conv_lifetime_capacity,
      conv_avg_annual_use=conv_avg_annual_use)
  assert ac.soln_lifetime_replacement == 50
  assert ac.conv_lifetime_replacement == pytest.approx(3333.333333333333)

def test_emissions_grid():
  ac = advanced_controls.AdvancedControls(emissions_grid_source="IPCC Only", emissions_grid_range="high")
  assert ac.emissions_grid_source == ef.GRID_SOURCE.IPCC
  assert ac.emissions_grid_range == ef.GRID_RANGE.HIGH
"""EOIP KPI analytics package."""

from eoip.analytics.kpi.base import (
    KPICalculator,
    KPIResult,
    KPIStatus,
    KPIWindow,
    insufficient_data_result,
    invalid_input_result,
    valid_result,
)
from eoip.analytics.kpi.capacity_factor import calculate_capacity_factor
from eoip.analytics.kpi.clipping import (
    calculate_clipping_loss_energy,
    calculate_clipping_loss_percentage,
)
from eoip.analytics.kpi.curtailment import (
    calculate_curtailed_energy,
    calculate_curtailment_percentage,
)
from eoip.analytics.kpi.downtime import (
    calculate_downtime_percentage,
    calculate_total_downtime,
)
from eoip.analytics.kpi.energy import (
    calculate_actual_energy,
    calculate_energy_achievement,
    calculate_energy_variance,
    calculate_expected_energy,
)
from eoip.analytics.kpi.financial import (
    calculate_budget_utilization,
    calculate_budget_variance,
    calculate_recoverable_revenue_opportunity,
    calculate_revenue,
    calculate_revenue_loss,
)
from eoip.analytics.kpi.grid_availability import (
    calculate_grid_availability,
)
from eoip.analytics.kpi.mtbf import calculate_mtbf
from eoip.analytics.kpi.mtta import calculate_mtta
from eoip.analytics.kpi.mttr import calculate_mttr
from eoip.analytics.kpi.performance_ratio import (
    calculate_performance_ratio,
)
from eoip.analytics.kpi.recoverable_energy import (
    calculate_recoverable_energy_opportunity,
    calculate_recoverable_energy_percentage,
)
from eoip.analytics.kpi.soiling import (
    calculate_soiling_loss_energy,
    calculate_soiling_loss_percentage,
)
from eoip.analytics.kpi.technical_availability import (
    calculate_technical_availability,
)

__all__ = [
    "KPICalculator",
    "KPIResult",
    "KPIStatus",
    "KPIWindow",
    "calculate_actual_energy",
    "calculate_budget_utilization",
    "calculate_budget_variance",
    "calculate_capacity_factor",
    "calculate_clipping_loss_energy",
    "calculate_clipping_loss_percentage",
    "calculate_curtailed_energy",
    "calculate_curtailment_percentage",
    "calculate_downtime_percentage",
    "calculate_energy_achievement",
    "calculate_energy_variance",
    "calculate_expected_energy",
    "calculate_grid_availability",
    "calculate_mtbf",
    "calculate_mtta",
    "calculate_mttr",
    "calculate_performance_ratio",
    "calculate_recoverable_energy_opportunity",
    "calculate_recoverable_energy_percentage",
    "calculate_recoverable_revenue_opportunity",
    "calculate_revenue",
    "calculate_revenue_loss",
    "calculate_soiling_loss_energy",
    "calculate_soiling_loss_percentage",
    "calculate_technical_availability",
    "calculate_total_downtime",
    "insufficient_data_result",
    "invalid_input_result",
    "valid_result",
]

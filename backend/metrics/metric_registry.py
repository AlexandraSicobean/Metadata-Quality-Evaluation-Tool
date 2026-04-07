from metrics.plugins.structural_completeness import StructuralCompletenessMetric
from metrics.plugins.property_completeness import PropertyCompletenessMetric


METRIC_REGISTRY = {
    "structural_completeness": StructuralCompletenessMetric,
    "property_completeness": PropertyCompletenessMetric
}
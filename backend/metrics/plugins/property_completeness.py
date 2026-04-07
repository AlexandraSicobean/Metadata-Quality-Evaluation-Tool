from collections import defaultdict
from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDF
import statistics

from metrics.metric_plugin import MetricPlugin
from models.dataset_context import DatasetContext
from models.metric_result import MetricResult
from metrics.metrics_exceptions import EmptyGraphError, NoTargetRecordsError


# Properties that are structural/administrative and uninformative
# for completeness analysis — present on every record by definition
EXCLUDED_PROPERTIES = {
    str(RDF.type),
}


def get_records_by_class(graph: Graph) -> dict[str, set[str]]:
    """
    Groups all named (non-blank) subjects by their rdf:type.

    Each record appears under every class it belongs to.
    Records with no type are grouped under 'Unknown'.
    """
    class_records: dict[str, set[str]] = defaultdict(set)

    for subject in graph.subjects():
        if isinstance(subject, BNode):
            continue

        types = [
            str(t) for t in graph.objects(subject, RDF.type)
            if not isinstance(t, BNode)
        ]

        if types:
            for t in types:
                class_records[t].add(str(subject))
        else:
            class_records["Unknown"].add(str(subject))

    return dict(class_records)


def compute_class_property_fill_rates(
    graph: Graph,
    class_records: dict[str, set[str]]
) -> dict[str, dict[str, dict]]:
    """
    For each class, computes per-property fill rates based only
    on records belonging to that class.

    Returns a nested structure:
        class_uri -> property_uri -> {present, missing, fill_rate}

    Properties in EXCLUDED_PROPERTIES are omitted.
    Results are sorted by fill_rate ascending within each class
    so the stacked bar chart renders the worst offenders first.
    """
    result = {}

    for class_uri, records in class_records.items():
        class_total = len(records)
        prop_counts: dict[str, set[str]] = defaultdict(set)

        for record_uri in records:
            for _, prop, _ in graph.triples(
                (URIRef(record_uri), None, None)
            ):
                prop_str = str(prop)
                if prop_str not in EXCLUDED_PROPERTIES:
                    prop_counts[prop_str].add(record_uri)

        class_fill_rates = {
            prop: {
                "present":   len(record_set),
                "missing":   class_total - len(record_set),
                "fill_rate": round(len(record_set) / class_total, 4)
            }
            for prop, record_set in prop_counts.items()
        }

        # Sort by fill_rate ascending — worst offenders first
        result[class_uri] = dict(
            sorted(
                class_fill_rates.items(),
                key=lambda x: x[1]["fill_rate"]
            )
        )

    return result


def compute_class_scores(
    class_property_fill_rates: dict[str, dict[str, dict]]
) -> dict[str, float]:
    """
    Computes the mean fill rate across all observed properties
    for each class.

    This is the per-class quality score used in the overall
    bar chart visualization.
    """
    return {
        class_uri: round(
            statistics.mean(
                prop["fill_rate"]
                for prop in props.values()
            ),
            4
        )
        for class_uri, props in class_property_fill_rates.items()
        if props
    }


def compute_overall_score(
    class_scores: dict[str, float],
    class_records: dict[str, set[str]]
) -> float:
    """
    Computes the overall dataset score as the weighted mean
    of per-class scores, weighted by number of records per class.

    This ensures a class with 1000 records influences the score
    more than a class with 5 records.
    """
    total_weighted = sum(
        class_scores[cls] * len(class_records[cls])
        for cls in class_scores
        if cls in class_records
    )
    total_weight = sum(
        len(class_records[cls])
        for cls in class_scores
        if cls in class_records
    )

    return round(total_weighted / total_weight, 4) if total_weight > 0 else 1.0


class PropertyCompletenessMetric(MetricPlugin):

    id          = "property_completeness"
    name        = "Property Completeness"
    description = (
        "Measures how consistently each property is used within "
        "each class across the dataset, without assuming a schema "
        "contract. Score is the weighted mean of per-class fill "
        "rates, weighted by number of records per class."
    )
    dimension    = "Contextual Quality"
    subdimension = "Completeness"
    weight       = 1.0

    def evaluate(self, context: DatasetContext) -> MetricResult:
        graph = context.graph

        if len(graph) == 0:
            raise EmptyGraphError(
                f"Dataset '{context.dataset_id}' contains an empty graph."
            )

        class_records = get_records_by_class(graph)

        if not class_records:
            raise NoTargetRecordsError(
                f"No typed records found in dataset "
                f"'{context.dataset_id}'."
            )

        class_property_fill_rates = compute_class_property_fill_rates(
            graph, class_records
        )

        class_scores = compute_class_scores(class_property_fill_rates)

        final_score = compute_overall_score(class_scores, class_records)

        details = {
            "total_records": sum(
                len(records) for records in class_records.values()
            ),
            "classes_found": {
                cls: len(records)
                for cls, records in class_records.items()
            },
            "class_scores":              class_scores,
            "class_property_fill_rates": class_property_fill_rates,
        }

        return MetricResult(
            metric_id=self.id,
            name=self.name,
            score=final_score,
            weight=self.weight,
            status="computed",
            details=details,
        )
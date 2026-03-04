from datasource.datasource_factory import DataSourceFactory
from metrics.metric_plugin import MetricPlugin
from models.dataset_context import DatasetContext

class EvaluationEngine:
    """
    Coordinator that orchestrates the metadata quality evaluation

    Operations:
    1. Loads RDF datasets using DataSourceFactory
    2. Creates Dataset Context objects
    3. Executes metric plugins over the dataset
    4. Aggregates all metrics into an overall score
    """

    def evaluate(self, datasets: list[dict], metrics: list[MetricPlugin]):
        """
        Executes the evaluation metrics over the provided datasets

        Parameters
        ----------
        datasets : list[dict]
            List of dataset descriptors from the frontend request.
            Each descriptor contains dataset metadata and a 
            source_config describing how the dataset should be loaded
        metrics: list[MetricPlugin]
            List of metric plugin instances that will be executed on
            each dataset

        Returns
        -------
        TODO: Return the aggregated result. Right now it only returns
        a list of metric results per dataset
        """
        all_dataset_results = []

        for dataset in datasets:
            # Load Graph
            datasource = DataSourceFactory.create(dataset["source_config"])
            graph = datasource.load()

            dataset_context = DatasetContext(
                dataset_id=dataset["dataset_id"],
                label=dataset.get("label"),
                graph=graph
            )

            # Run metrics
            metric_results = []
            for metric in metrics:
                result = metric.evaluate(dataset_context)
                metric_results.append(result)

            all_dataset_results.append(metric_results)

            # Aggregate results - TO BE IMPLEMENTED

        return all_dataset_results
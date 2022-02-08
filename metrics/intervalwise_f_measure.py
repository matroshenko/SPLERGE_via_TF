import tensorflow.keras as keras
import igraph

from utils.interval import Interval, get_intervals_of_ones


class IntervalwiseFMeasure(keras.metrics.Metric):
    def __init__(self, name=None):
        super().__init__(name=name)
        self.markup_intervals_count = self.add_weight('markup_intervals_count', initializer='zeros', dtype='int32')
        self.predicted_intervals_count = self.add_weight('predicted_intervals_count', initializer='zeros', dtype='int32')
        self.matched_intervals_count = self.add_weight('matched_intervals_count', initializer='zeros', dtype='int32')

    def update_state(self, markup_mask, predicted_mask, sample_weight=None):
        assert len(markup_mask.shape) == 2
        assert len(predicted_mask.shape) == 2
        for markup_mask_element, predicted_mask_element in zip(markup_mask, predicted_mask):
            markup_intervals = get_intervals_of_ones(markup_mask_element.numpy())
            predicted_intervals = get_intervals_of_ones(predicted_mask_element.numpy())
            matching_size = self._calculate_matching_size(markup_intervals, predicted_intervals)

            self.markup_intervals_count.assign_add(len(markup_intervals))
            self.predicted_intervals_count.assign_add(len(predicted_intervals))
            self.matched_intervals_count.assign_add(matching_size)

    def result(self):
        if self.matched_intervals_count == 0:
            return 0
        assert self.markup_intervals_count > 0
        assert self.predicted_intervals_count > 0
        recall = self.matched_intervals_count / self.markup_intervals_count
        precision = self.matched_intervals_count / self.predicted_intervals_count
        return 2 * recall * precision / (recall + precision)

    @staticmethod
    def _calculate_matching_size(first_intervals_list, second_intervals_list):
        graph = igraph.Graph()
        n = len(first_intervals_list)
        m = len(second_intervals_list)
        graph.add_vertices(n + m, attributes={'type': [0] * n + [1] * m})

        edges = []
        for i, interval1 in enumerate(first_intervals_list):
            for j, interval2 in enumerate(second_intervals_list):
                intersection_length = Interval.get_intersection_length(interval1, interval2)
                min_length = min(interval1.get_length(), interval2.get_length())
                assert min_length > 0
                if intersection_length / min_length > 0.5:
                    edges.append((i, n+j))
        graph.add_edges(edges)
        matching = graph.maximum_bipartite_matching()
        return len(matching)
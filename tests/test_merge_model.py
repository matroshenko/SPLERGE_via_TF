from unittest import TestCase, main

import tensorflow as tf

import context
from merge.model import Model
from datasets.ICDAR.grid_structure import GridStructureBuilder
from datasets.ICDAR.rect import Rect


class ModelTestCase(TestCase):
    def test_output_shape(self):
        tf.random.set_seed(42)

        batch_size = 1
        height = 200
        width = 1000
        inputs = {
            'image': tf.random.uniform(shape=(batch_size, height, width, 3), minval=0, maxval=256, dtype='int32'),
            'horz_split_points_probs': tf.random.uniform(shape=(batch_size, height), dtype='float32'),
            'vert_split_points_probs': tf.random.uniform(shape=(batch_size, width), dtype='float32'),
            'horz_split_points_binary': tf.random.uniform(shape=(batch_size, height), minval=0, maxval=2, dtype='int32'),
            'vert_split_points_binary': tf.random.uniform(shape=(batch_size, width), minval=0, maxval=2, dtype='int32')
        }

        model = Model()
        outputs = model(inputs)

        grid = GridStructureBuilder(
            Rect(0, 0, width, height), 
            tf.squeeze(inputs['horz_split_points_binary'], axis=0).numpy(), 
            tf.squeeze(inputs['vert_split_points_binary'], axis=0).numpy()
        ).build()
        expected_merge_down_shape = (batch_size, grid.get_rows_count()-1, grid.get_cols_count())
        expected_merge_right_shape = (batch_size, grid.get_rows_count(), grid.get_cols_count()-1)

        self.assertEqual(
            outputs['merge_down_probs1'].shape, expected_merge_down_shape)
        self.assertEqual(
            outputs['merge_down_probs2'].shape, expected_merge_down_shape)
        self.assertEqual(
            outputs['merge_right_probs1'].shape, expected_merge_right_shape)
        self.assertEqual(
            outputs['merge_right_probs2'].shape, expected_merge_right_shape)

if __name__ == '__main__':
    main()
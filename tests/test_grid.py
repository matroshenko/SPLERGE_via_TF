from unittest import TestCase, main

import context
from datasets.ICDAR.grid import Grid
from datasets.ICDAR.rect import Rect


class GridTest(TestCase):
    def test_create_by_rect_and_masks(self):
        rect = Rect(2, 1, 19, 12)
        h_mask = [0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0]
        v_mask = [0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0]
        grid = Grid.create_by_rect_and_masks(rect, h_mask, v_mask)
        expected_grid = Grid([1, 3, 5, 7, 9, 12], [2, 7, 11, 15, 19])
        self.assertEqual(grid, expected_grid)


if __name__ == '__main__':
    main()
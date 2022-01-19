"""ICDAR dataset."""

from collections import namedtuple
import tensorflow_datasets as tfds
import xml.etree.ElementTree as ET
import pdf2image
import PIL
import io

# TODO(ICDAR): Markdown description  that will appear on the catalog page.
_DESCRIPTION = """
Description is **formatted** as markdown.

It should also contain any processing which has been applied (if any),
(e.g. corrupted example skipped, images cropped,...):
"""

# TODO(ICDAR): BibTeX citation
_CITATION = """
"""

class Icdar(tfds.core.GeneratorBasedBuilder):
  """DatasetBuilder for ICDAR dataset."""

  VERSION = tfds.core.Version('1.0.0')
  RELEASE_NOTES = {
      '1.0.0': 'Initial release.',
  }

  def _info(self) -> tfds.core.DatasetInfo:
    """Returns the dataset metadata."""

    return tfds.core.DatasetInfo(
        builder=self,
        description=_DESCRIPTION,
        features=tfds.features.FeaturesDict({
            # These are the features of your dataset like images, labels ...
            'image': tfds.features.Image(shape=(None, None, 3)),
            'horz_split_points': tfds.features.Image(shape=(None, None, 1)),
            'vert_split_points': tfds.features.Image(shape=(None, None, 1))
        }),
        homepage='https://www.tamirhassan.com/html/dataset.html',
        citation=_CITATION,
        disable_shuffling=True
    )

  def _split_generators(self, dl_manager: tfds.download.DownloadManager):
    """Returns SplitGenerators."""

    path = dl_manager.download_and_extract(
      'https://www.tamirhassan.com/html/files/icdar2013-competition-dataset-with-gt.zip')

    return {
        'train': self._generate_examples(path)
    }

  def _generate_examples(self, path):
    """Yields examples."""

    for pdf_file_path in path.glob('*.pdf'):
      stem = pdf_file_path.stem
      region_file_path = pdf_file_path.with_name(stem + '-reg.xml')
      structure_file_path = pdf_file_path.with_name(stem + '-str.xml')

      pages = pdf2image.convert_from_path(pdf_file_path, dpi=72)
      for page_number, table in self._generate_tables(pages[0].height, region_file_path, structure_file_path):
        key = '{}-{}'.format(stem, table.id)
        page = pages[page_number]
        table_image = page.crop(table.rect)
        horz_split_points_image = table.create_horz_split_points_image()
        vert_split_points_image = table.create_vert_split_points_image()
        self._dump_debug_image(table.id, table_image, horz_split_points_image, vert_split_points_image)
        yield key, {
          'image': self._image_to_byte_array(table_image),
          'horz_split_points': self._image_to_byte_array(horz_split_points_image),
          'vert_split_points': self._image_to_byte_array(vert_split_points_image)
        }

  def _generate_tables(self, page_height, region_file_path, structure_file_path):
    regions_tree = ET.parse(region_file_path)
    structures_tree = ET.parse(structure_file_path)
    for table_node, table_structure_node in zip(regions_tree.getroot(), structures_tree.getroot()):
      table_id = int(table_node.get('id'))
      region_node = table_node.find('region')
      page_number = int(region_node.get('page')) - 1
      table_rect = self._get_bounding_box(page_height, region_node)
      cells_node = table_structure_node.find('region')
      cells = [self._get_cell(page_height, node) for node in cells_node]
      yield page_number, Table(table_id, table_rect, cells)

  def _get_bounding_box(self, page_height, xml_node):
    bounding_box_node = xml_node.find('bounding-box')
    left = int(bounding_box_node.get('x1'))
    top = page_height - int(bounding_box_node.get('y2'))
    right = int(bounding_box_node.get('x2'))
    bottom = page_height - int(bounding_box_node.get('y1'))
    return Rect(left, top, right, bottom)

  def _get_cell(self, page_height, xml_node):
    rect = self._get_bounding_box(page_height, xml_node)
    col_start = int(xml_node.get('start-col'))
    col_end = int(xml_node.get('end-col', col_start))
    row_start = int(xml_node.get('start-row'))
    row_end = int(xml_node.get('end-row', row_start))
    return Cell(rect, col_start, col_end, row_start, row_end)

  def _image_to_byte_array(self, image):
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, format='png')
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr

  def _dump_debug_image(self, table_id, table_image, horz_split_points_image, vert_split_points_image):
    table_image.save('table_{}.png'.format(table_id))
    horz_split_points_image.save('horz_split_points_{}.png'.format(table_id))
    vert_split_points_image.save('vert_split_points_{}.png'.format(table_id))


Rect = namedtuple('Rect', ['left', 'top', 'right', 'bottom'])


class Cell(object):
  def __init__(self, rect, col_start, col_end, row_start, row_end):
    self.rect = rect
    self.col_start = col_start
    self.col_end = col_end
    self.row_start = row_start
    self.row_end = row_end


class Table(object):
  def __init__(self, id, rect, cells):
    self.id = id
    self.rect = rect
    self.cells = cells

  def create_horz_split_points_image(self):
    width = self.rect.right - self.rect.left
    height = self.rect.bottom - self.rect.top
    result = PIL.Image.new('L', (width, height))

    split_point_index = 0
    while True:
      top_adjacent_cells = self._get_top_adjacent_cells(split_point_index)
      bottom_adjacent_cells = self._get_bottom_adjacent_cells(split_point_index)
      if not bottom_adjacent_cells:
        break
      assert top_adjacent_cells
      split_point_interval = (
        max(cell.rect.bottom - self.rect.top for cell in top_adjacent_cells), 
        min(cell.rect.top - self.rect.top for cell in bottom_adjacent_cells)
      )
      self._draw_horz_white_strip(split_point_interval, result)

      split_point_index += 1

    return result

  def create_vert_split_points_image(self):
    width = self.rect.right - self.rect.left
    height = self.rect.bottom - self.rect.top
    result = PIL.Image.new('L', (width, height))

    split_point_index = 0
    while True:
      left_adjacent_cells = self._get_left_adjacent_cells(split_point_index)
      right_adjacent_cells = self._get_right_adjacent_cells(split_point_index)
      if not right_adjacent_cells:
        break
      assert left_adjacent_cells
      split_point_interval = (
        max(cell.rect.right - self.rect.left for cell in left_adjacent_cells), 
        min(cell.rect.left - self.rect.left for cell in right_adjacent_cells)
      )
      self._draw_vert_white_strip(split_point_interval, result)

      split_point_index += 1

    return result

  def _draw_vert_white_strip(self, interval, image):
    pixels = image.load()
    for i in range(image.height):
      for j in range(interval[0], interval[1]):
        pixels[j, i] = 255

  def _draw_horz_white_strip(self, interval, image):
    pixels = image.load()
    for i in range(interval[0], interval[1]):
      for j in range(image.width):
        pixels[j, i] = 255

  def _get_left_adjacent_cells(self, vert_split_point_index):
    result = []
    for cell in self.cells:
      if cell.col_end == vert_split_point_index:
        result.append(cell)
    return result

  def _get_right_adjacent_cells(self, vert_split_point_index):
    result = []
    for cell in self.cells:
      if cell.col_start == vert_split_point_index + 1:
        result.append(cell)
    return result

  def _get_top_adjacent_cells(self, horz_split_point_index):
    result = []
    for cell in self.cells:
      if cell.row_end == horz_split_point_index:
        result.append(cell)
    return result

  def _get_bottom_adjacent_cells(self, horz_split_point_index):
    result = []
    for cell in self.cells:
      if cell.row_start == horz_split_point_index + 1:
        result.append(cell)
    return result

from .topology import BaseTopology
from .vertex_attributes import BaseVertexAttributes, PeriodicAttributes
from ..utils.decorators import sampy_class
import xml.etree.ElementTree as ET
import numpy as np


@sampy_class
class GraphFromORMxml(BaseTopology,
                      BaseVertexAttributes,
                      PeriodicAttributes):
    """
    Class developed for the need of the Leighton Lab. The graph structure is read from an XML, as generated by Badr
    QGIS module.
    """
    def __init__(self, path_to_xml=None):
        if path_to_xml is None:
            raise ValueError("A path to an ORM XML should be provided.")

        tree = ET.parse(path_to_xml)
        root = tree.getroot()

        # get super_cells info
        self.dict_super_cell = {}
        counter = 0
        for super_cell in root.findall('SuperCells'):
            temp_dict = {}
            for info in super_cell:
                temp_dict[info.tag] = info.text
            self.dict_super_cell[temp_dict['ID']] = {'index': counter,
                                                     'in_res': float(temp_dict['InResistance'])/100.,
                                                     'out_res': float(temp_dict['OutResistance'])/100.}
            counter += 1

        # read the various parameters to create a sampy graph
        set_neighbours_tags = {'N', 'NE', 'NW', 'S', 'SE', 'SW'}
        counter = 0
        for cell in root.findall('AllCellData'):
            id_cell = cell.find('HEXID').text
            if id_cell not in self.dict_cell_id_to_ind:
                self.dict_cell_id_to_ind[id_cell] = counter
                counter += 1
            else:
                raise ValueError("The cell " + id_cell + " is defined two times in the xml.")

        self.connections = np.full((counter, 6), -1, dtype=np.int32)
        self.weights = np.full((counter, 6), -1.)
        self.df_attributes['K'] = np.full((counter,), 0.)
        self.df_attributes['in_res'] = np.full((counter,), 0.)
        self.df_attributes['out_res'] = np.full((counter,), 0.)
        self.df_attributes['super_cell'] = np.full((counter,), 0)
        self.df_attributes['easting'] = np.full((counter,), 0.)
        self.df_attributes['northing'] = np.full((counter,), 0.)
        array_nb_neighbours = np.full((counter,), 0, dtype=np.int8)

        for cell in root.findall('AllCellData'):
            index_cell = self.dict_cell_id_to_ind[cell.find('HEXID').text]
            for info in cell:
                if info.tag in set_neighbours_tags:
                    if info.text != 'b' and info.text in self.dict_cell_id_to_ind:
                        self.connections[index_cell][array_nb_neighbours[index_cell]] = \
                            self.dict_cell_id_to_ind[info.text]
                        array_nb_neighbours[index_cell] += 1
                elif info.tag == 'K':
                    self.df_attributes['K'][index_cell] = float(info.text)
                elif info.tag == 'supercell':
                    self.df_attributes['super_cell'][index_cell] = self.dict_super_cell[info.text]['index']
                    self.df_attributes['in_res'][index_cell] = self.dict_super_cell[info.text]['in_res']
                    self.df_attributes['out_res'][index_cell] = self.dict_super_cell[info.text]['out_res']
                elif info.tag == 'easting':
                    self.df_attributes['easting'][index_cell] = float(info.text)
                elif info.tag == 'northing':
                    self.df_attributes['northing'][index_cell] = float(info.text)

        # we now populate the weights array
        for i in range(self.connections.shape[0]):
            nb_neighbours = array_nb_neighbours[i]
            if nb_neighbours == 0:
                continue
            for j in range(nb_neighbours - 1):
                self.weights[i][j] = float(j + 1)/float(nb_neighbours)
            self.weights[i][nb_neighbours - 1] = 1.

    def get_super_cell(self, name_super_cell):
        return self.df_attributes['super_cell'] == self.dict_super_cell[name_super_cell]['index']

    @property
    def list_super_cell_names(self):
        return [super_cell_name for super_cell_name in self.dict_super_cell]

#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) [YEAR] [YOUR NAME], [YOUR EMAIL]
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
Description of this extension
"""

import logging
from typing import Any, Dict, List, Union
import inkex
import re
from inkex.utils import debug as alert
import inkex.elements._polygons as polygons
import inkex.elements._selected as selected

from enum import Enum
from typing import Union, Optional, TypeVar, Type

T = TypeVar('T', bound='DictLikeEnum')

class DictLikeEnum(Enum):
    """An Enum class with dict-like get method."""
    # Alternative if you want to get by value instead of name:
    @classmethod
    def get(cls: Type[T], value: Union[str, int], default: Union[None, T] = None) -> Optional[T]:
        """
        Get an enum member by its actual value.
        
        Args:
            value: The value to look up
            
        Returns:
            The corresponding enum member or None if not found
        """
        try:
            return cls(value)  # Access by value
        except ValueError:
            return None


class FlutterMapExtension(inkex.EffectExtension):
    POINT_ID_REGEX = re.compile(r'^point-(\d+)(?:=([\d-]*))?$')
    # point-43=44-39-45
    # │     │  └‒‒└‒‒└‒‒‒‒‒ unique IDs of connected neighbors
    # │     └‒‒‒‒‒ unique ID of the object
    # └‒‒‒‒‒ class of the object - point
    
    # The following regex correctly matches the following texts (excluding the last one):
    # stairs-elevator-1=2
    # shop-1=3000
    # warehouse-hallway-4=04444
    # pointless-5000=1
    # point-5=6 (not matched, as expected)
    BUILDING_ID_REGEX = re.compile(r'^((?!point-)[a-zA-Z]+)-(?:([a-zA-Z]+)-)?(\d+)=([\d]+)$')
    # stairs-elevator-1=2
    # │      │        │ └‒‒‒‒‒ unique ID of the connected entrance point (there can be only one)
    # │      │        └‒‒‒‒‒ unique ID of the object
    # │      └‒‒‒‒‒ subtype of the object (required for stairs and toilet)
    # └‒‒‒‒‒ class of the object
    
    @classmethod
    def get_building_id_number(cls, id_attr: str) -> Union[int, None]:
        """
        Extracts the numeric ID from a building ID attribute."""
        matches = cls.BUILDING_ID_REGEX.match(id_attr)
        if not matches:
            return None
        return int(matches.group(3))
    
    @classmethod
    def get_point_id_number(cls, id_attr: str) -> Union[int, None]:
        """
        Extracts the numeric ID from a point ID attribute."""
        matches = cls.POINT_ID_REGEX.match(id_attr)
        if not matches:
            return None
        return int(matches.group(1))

    from typing import Callable, Collection
    @staticmethod
    def get_max_existing_object_id(ids_set:Collection, id_number_provider: Callable[[str], Union[int, None]]) -> int:
        """
        Generic method to get the maximum existing object ID number from a set of IDs,
        using a provided function to extract the numeric ID from each ID string.
        """
        max_object_id_number = 0
        for id in ids_set:
            object_number: Union[int, None] = id_number_provider(id)

            # skip non-matching ids
            if object_number is None:
                continue

            if object_number > max_object_id_number:
                max_object_id_number = object_number
        
        return max_object_id_number


    class SmartConnectTypes(DictLikeEnum):
        """Smart connect algorithms supported by the extension."""
        NEAREST_POINT = 'nearest_point'


    class PointConnectionOptions:

        class SortMode(DictLikeEnum):
            NO_SORT = 'no_sort'
            X_AXIS = 'sort_horizontally'
            Y_AXIS = 'sort_vertically'

        class SortDirection(DictLikeEnum):
            ASCENDING = 'asc'
            DESCENDING = 'desc'

        def __init__(self,
                     draw_lines: bool = True, 
                     line_color: inkex.Color = inkex.Color('lightblue'),
                     lines_stroke:float = 0.1, 
                     copy_transform: str = 'no_copy', 
                     sort_mode: SortMode = SortMode.NO_SORT,
                     sort_direction: SortDirection = SortDirection.ASCENDING,
                     ):
            self.draw_lines = draw_lines
            self.line_color = line_color
            self.lines_stroke = lines_stroke
            self.copy_transform = copy_transform
            self.sort_mode = sort_mode
            self.sort_direction = sort_direction

        @classmethod
        def from_extension_options(cls, options) -> 'FlutterMapExtension.PointConnectionOptions':

            # get unit number and id from text expression
            stroke_width_value, stroke_width_unit = FlutterMapExtension.extract_unit_from_text_expression(options.line_stroke_width)
            if (stroke_width_value is None) or (stroke_width_unit is None):
                raise inkex.AbortExtension(f'invalid units value provided for stroke width: "{options.line_stroke_width}"')

            from inkex.units import convert_unit

            sort_mode = cls.SortMode.get(options.sort_mode)
            assert sort_mode, f'invalid sort_mode value provided: {options.sort_mode}. Valid values: {[e.value for e in cls.SortMode]}'

            sort_direction = cls.SortDirection.get(options.sort_direction)
            assert sort_direction, f'invalid sort_direction value provided: {options.sort_mode}. Valid values: {[e.value for e in cls.SortDirection]}'

            return FlutterMapExtension.PointConnectionOptions(
                draw_lines=options.draw_lines,
                line_color=options.line_color,
                lines_stroke= convert_unit(stroke_width_value, stroke_width_unit),
                copy_transform=options.copy_transform,
                sort_mode = sort_mode,
                sort_direction = sort_direction
            )
    class EntrancePointOptions:
        def __init__(self,
                     draw_point: bool = True, 
                     point_fill_color: inkex.Color = inkex.Color('black'),
                     point_radius: float = 0.1,
                     point_stroke_color: inkex.Color = inkex.Color('red'),
                     point_stroke:float = 0.1, 
                     ):
            self.draw_point= draw_point
            self.point_fill_color = point_fill_color
            self.point_radius = point_radius
            self.point_stroke_color = point_stroke_color
            self.point_stroke = point_stroke

        @staticmethod
        def from_extension_options(options) -> 'FlutterMapExtension.EntrancePointOptions':

            # get unit number and id from text expression
            stroke_width_value, stroke_width_unit = FlutterMapExtension.extract_unit_from_text_expression(options.point_stroke)
            if (stroke_width_value is None) or (stroke_width_unit is None):
                raise inkex.AbortExtension(f'invalid units value provided for stroke width: "{options.point_stroke}"')
            
            point_radius_value, point_radius_unit = FlutterMapExtension.extract_unit_from_text_expression(options.point_radius)
            if (point_radius_value is None) or (point_radius_unit is None):
                raise inkex.AbortExtension(f'invalid units value provided for point radius: "{options.point_radius}"')

            from inkex.units import convert_unit

            return FlutterMapExtension.EntrancePointOptions(
                draw_point= True,
                point_fill_color= options.point_fill_color,
                point_radius= convert_unit(point_radius_value, point_radius_unit),
                point_stroke_color= options.point_stroke_color,
                point_stroke= convert_unit(stroke_width_value, stroke_width_unit),
            )

    class BuildingOptions:
        class BuildingType(DictLikeEnum):
            '''
            Building types supported by the extension.
            Value corresponds to the string used in the extension options. 
            value follows the format: '<type>-<subtype>'
            '''
            SHOP = 'shop'
            PARKING = 'parking'
            ATM_MACHINE = 'atmmachine'
            TOILET_MALE = 'toilet-male'
            TOILET_FEMALE = 'toilet-female'
            TOILET_MATHERNITY = 'toilet-mathernity'
            SIMPLE_STAIRS = 'simple-stais'
            FIRE_ESCAPE_STAIRS = 'fire_escape-stais'
            ESCALATOR_STAIRS = 'escalator-stairs'
            ELEVATOR_STAIRS = 'elevator-stairs'
            CUSTOM = 'custom'

        class PointPosition(DictLikeEnum):
            UPPER_LEFT = 'upper-left'
            UPPER_CENTER = 'upper-center'
            UPPER_RIGHT = 'upper-right'
            CENTER_LEFT = 'center-left'
            CENTER = 'center'
            CENTER_RIGHT = 'center-right'
            LOWER_LEFT = 'lower-left'
            LOWER_CENTER = 'lower-center'
            LOWER_RIGHT = 'lower-right'

        class PointToBorderSeparation(DictLikeEnum):
            CENTER_TO_CENTER = 'center-to-center'
            BORDER_TO_BORDER_IN = 'border-to-border-in'
            BORDER_TO_BORDER_OUT = 'border-to-boder-out'
            TEN_PERCENT_TO_BORDER_IN = '10%-to-border-in'
            TEN_PERCENT_TO_BORDER_OUT = '10%-to-border-out'
            CUSTOM = 'custom'

        def __init__(self,
                     building_type: str= 'shop',
                     custom_type: Union[str, None] = None,  
                     custom_subtype: str = '',  
                     add_connection_point: bool = True,
                     building_point_position: str = 'center',
                     point_to_border_separation: str = 'border-to-boder-out',
                     custom_point_separation: str = '10px-in-border',
                     ):
            
            # Validate building_type parameters

            # Try to parse default building type from string
            self.building_type = self.BuildingType.get(building_type, None)
            assert self.building_type, f"Invalid building_type: {building_type}. Valid values are {[bt.value for bt in FlutterMapExtension.BuildingOptions.BuildingType]}"
            
            # If building type is custom, ensure custom_type is provided
            if self.building_type == self.BuildingType.CUSTOM:
                assert custom_type and len(custom_type) > 0, "custom_type is required when building_type is 'custom'"
                self.custom_type = custom_type
            else:
                self.custom_type = None
            
            self.custom_subtype = custom_subtype if custom_subtype and len(custom_subtype) > 0 else None
            # TODO: Verify this validation of length is required
            assert self.custom_subtype is None or len(self.custom_subtype) > 30 or self.custom_subtype is None, "custom_subtype must be at least 4 characters long if provided"
            
            # Validate required add_connection_point parameter
            assert add_connection_point in [True, False], "add_connection_point is required & must be a boolean"

            self.add_connection_point = add_connection_point
            if not add_connection_point:
                # If not adding connection point, skip further validations
                self.building_point_position = None
                self.point_to_border_separation = None
                self.custom_point_separation = None
                return

            # Validate point position parameters

            self.building_point_position = self.PointPosition.get(building_point_position, None)
            assert building_point_position, f"Invalid building_point_position value: '{building_point_position}'. Valid values are " + ", ".join([bp.value for bp in FlutterMapExtension.BuildingOptions.PointPosition])


            self.point_to_border_separation = self.PointToBorderSeparation.get(point_to_border_separation, None)
            assert self.point_to_border_separation, f"Invalid point_to_border_separation value: '{point_to_border_separation}'. Valid values are " + ", ".join([pts.value for pts in FlutterMapExtension.BuildingOptions.PointToBorderSeparation])

            if self.point_to_border_separation == self.PointToBorderSeparation.CUSTOM:
                assert custom_point_separation and len(custom_point_separation) > 0, "custom point separation is required when point_to_border_separation is 'custom'"
                self.custom_point_separation = custom_point_separation
            else:
                self.custom_point_separation = None
            pass
                 
        @staticmethod
        def from_extension_options(options) -> 'FlutterMapExtension.BuildingOptions':
            return FlutterMapExtension.BuildingOptions(
                building_type=options.building_type,
                custom_type=options.custom_type,
                custom_subtype=options.custom_subtype,
                add_connection_point=options.add_connection_point,
                building_point_position=options.building_point_position,
                point_to_border_separation=options.point_to_border_separation,
                custom_point_separation=options.custom_point_separation,
            )

    @staticmethod
    def get_next_object_id(existing_max):
        return existing_max + 1

    @staticmethod
    def parse_point_id(id_attr) -> tuple[Union[int, None], List[int]]:
        
        """
        Receives an element ID and returns its unique id number and the linked elements id numbers

        - If the element has not defined ID return (None, [])
        - If the element does not matches the special pattern return (None, [])
        - If the element have any linked oelement id return (unique_id, [])

        :return Set: (current_element_id, linked_elements_id_list)
        """
        # If the element does not have id, it means it has not linked elements
        if not id_attr:
            return (None, [])


        id_match = FlutterMapExtension.POINT_ID_REGEX.match(id_attr)
        # If the id does not matches our pattern it is not a point element
        if not id_match:
            return (None, [])

        unique_id_number = int(id_match.group(1))

        linked_elements_substring = id_match.group(2)
        if not linked_elements_substring:
            return (unique_id_number, [])

        linked_elements_id_list = [int(linked_id) for linked_id in linked_elements_substring.split('-')]

        return (unique_id_number, linked_elements_id_list)

    @staticmethod
    def parse_building_id(id_attr) -> tuple[Union[str, None], Union[str, None], Union[int, None], List[int],]:
        """
        Receives a building element ID and returns its unique id number, 
        linked elements id numbers, building class, and subtype.
        
        - If the element has no ID attribute, return (None, None, None, [])
        - If the element doesn't match the building pattern, return (None, None, None, [])
        - Returns: (building_type, building_subtype, current_element_id, linked_elements_id_list)
        
        :return: (building_type, building_subtype, current_element_id, linked_elements_id_list)
        """
        # If the element does not have id, it means it has not been properly identified
        if not id_attr:
            return (None, None, None, [])
        
        # Try to match building pattern
        building_match = FlutterMapExtension.BUILDING_ID_REGEX.match(id_attr)
        if not building_match:
            return (None, None, None, [])
        
        # Extract building components
        building_type = building_match.group(1)  # e.g., "stairs", "shop"
        building_subtype = building_match.group(2)  # e.g., "elevator", "male" or None
        unique_id_str = building_match.group(3)   # ID as string
        connections_str = building_match.group(4)  # Connections as string
        
        # Parse unique ID
        unique_id_number = int(unique_id_str)
        
        # Parse linked elements (left as list of integers as tough to a future use case allowing buildings to have multiple entrances/point relationships)
        linked_elements_id_list = []
        if connections_str:
            for linked_id in connections_str.split('-'):
                linked_elements_id_list.append(int(linked_id))
                # Skip invalid connection IDs but continue parsing
                continue
        
        return (building_type, building_subtype, unique_id_number, linked_elements_id_list)

    @staticmethod
    def build_point_id_attr(id, neighbors_list):
        if neighbors_list:
            neighbors_list_str = {str(n) for n in neighbors_list}
            return f"point-{id}={'-'.join(neighbors_list_str)}"
        else:
            return f"point-{id}"
    
    @staticmethod
    def build_building_id_attr(building_type: str, building_subtype: Union[str, None, ], id: int, entrance_ids: List[int]): 
        # Optional subtype and entrances id list
        return f"{building_type}-" + \
                (f"{building_subtype}-" if building_subtype else "") + \
                f"{id}=" + \
                ('-'.join([str(eid) for eid in entrance_ids]) if entrance_ids else '')

    @staticmethod
    def extract_unit_from_text_expression(text:str) -> tuple[Union[float, None], Union[str, None]]:
        """
        Takes a string representing a unit expression (e.g., "10mm", "5.5in") and extracts the numeric value and unit identifier.

        Return a tuple (number, unit_id) if successful, or (None, None) if the input is invalid.
        tuple is tough to be used with inkex.units.convert_unit function.
        """
        logger = logging.getLogger()


        UNITS_REGEX = r'^(\d+\.?\d*)(px|mm|cm|m|in)'
        units_re = re.compile(UNITS_REGEX)

        match = units_re.match(text)

        # Fail fast
        if not match: 
            logger .warning(f'Units expresion did not match regex {UNITS_REGEX=}: {text}')
            return None, None

        # extract values in case of match
        try:
            unit_num = float(match.group(1))
            unit_id = match.group(2)
        except ValueError:
            logger .warning(f'Error converting unit number to float from match groups: {match.groups()}')
            return None, None
        except Exception:
            logger .warning(f'Error extracting unit values from match groups: {match.groups()}')
            return None, None
            
        return float(unit_num), unit_id


    def add_arguments(self, pars):
        pars.add_argument("--tab", choices=["Operation Mode", "Options", "Help", "building_options"])
        # Operation Mode tab
        pars.add_argument("--operation_mode", choices=["connect", "clean", "add_building"], default="connect")

        # Connection options
        pars.add_argument("--clean_lines", type=inkex.Boolean, default=True)
        pars.add_argument("--draw_lines", type=inkex.Boolean, default=True)
        pars.add_argument("--line_color", type=inkex.Color, default=inkex.Color('lightblue'))
        pars.add_argument("--line_stroke_width", type=str, default='0.01px')
        pars.add_argument("--copy_transform", choices=['copy_from_a', 'copy_from_b', 'no_copy', 'copy_from_both'], type=str, default='no_copy')
        # Sorting options
        pars.add_argument("--sort_mode", choices=['no_sort', 'sort_horizontally', 'sort_vertically'], type=str, default='no_sort')
        pars.add_argument("--sort_direction", choices=['asc', 'desc'], type=str, default='asc')

        # Building type options
        pars.add_argument("--building_type", choices=['shop', 'parking', 'atmmachine', 'toilet-male', 'toilet-female', 
                                                    'toilet-mathernity', 'simple-stais', 'fire_escape-stais', 
                                                    'escalator-stairs', 'elevator-stairs', 'custom'], 
                        type=str, default='shop')
        pars.add_argument("--custom_type", type=str, default='')
        pars.add_argument("--custom_subtype", type=str, default='')

        # Building point options
        pars.add_argument("--add_connection_point", type=inkex.Boolean, default=True)
        pars.add_argument("--point_radius", type=str, default='0.01')
        pars.add_argument("--point_fill_color", type=inkex.Color, default=inkex.Color('black'))
        pars.add_argument("--point_stroke", type=str, default='0.01')
        pars.add_argument("--point_stroke_color", type=inkex.Color, default=inkex.Color('red'))

        pars.add_argument("--building_point_position", 
                        choices=['center-left', 'center-right', 'center', 'upper-left', 'upper-right', 
                                'upper-center', 'lower-left', 'lower-right', 'lower-center'], 
                        type=str, default='center')
        pars.add_argument("--point_to_border_separation", 
                        choices=['center-to-center', 'border-to-border-in', 'border-to-boder-out', 
                                '10%-to-border-in', '10%-to-border-out'], 
                        type=str, default='border-to-boder-out')
        pars.add_argument("--custom_point_separation", type=str, default='10px-in-border')

        # Smart Connect parameters
        pars.add_argument("--smart_connect_enabled", type=inkex.Boolean, default=False)
        pars.add_argument("--smart_connect_type", type=str, default="nearest_point")
        
        # Nearest point connection options
        pars.add_argument("--ignore_building_point", type=inkex.Boolean, default=True)
        pars.add_argument("--max_radius", type=str, default="0.1px")

    

    def effect(self):
        """ Main entry point of the extension """
        # Determine operation mode
        operation_mode = str(self.options.operation_mode).lower()

        if operation_mode == 'connect':
            if self.options.smart_connect_enabled:
                smart_connect_type = self.SmartConnectTypes.get(self.options.smart_connect_type)
                assert smart_connect_type is not None, f'Invalid smart connect type: {self.options.smart_connect_type}'

                self.smart_connect_points(
                    smart_connect_type= smart_connect_type,
                    ignore_building_point= self.options.ignore_building_point,
                    max_radius= self.options.max_radius,
                )
            else: 
                self.connect_points(
                    connection_options= FlutterMapExtension.PointConnectionOptions.from_extension_options(self.options),
                )
        elif operation_mode == 'clean':
            self.clean_point_connections(
                clean_lines=self.options.clean_lines
            )
        elif operation_mode == 'add_building':

            # get unit number and id from text expression
            entrance_radius_value, entrance_radius_units = FlutterMapExtension.extract_unit_from_text_expression(self.options.point_radius)
            if (entrance_radius_value is None) or (entrance_radius_units is None):
                raise inkex.AbortExtension(f'invalid units value provided for entrance point radius: "{self.options.point_radius}"')

            from inkex.units import convert_unit
            final_point_radius = convert_unit(entrance_radius_value, entrance_radius_units)

            self.add_building(
                building_options= FlutterMapExtension.BuildingOptions.from_extension_options(self.options),
                entrance_point_options= FlutterMapExtension.EntrancePointOptions.from_extension_options(self.options),
                sort_mode= self.options.sort_mode,
                sort_direction= self.options.sort_direction,
            )
        else:
            raise NotImplementedError(f'Operation Mode not implemented: {self.options.operation_mode}')

    def clean_point_connections(self, clean_lines: bool = True):
        """
        Deletes lines connected to points that no longer exist (using numeric IDs),
        and cleans up neighbors in point IDs.
        Lines without flutter_maps:a_id/b_id are skipped.
        """
        # TODO: Add functionality to clean building to point connections as well.

        layer = self.svg.get_current_layer()

        # Gather all numeric point IDs from the document
        # mapps custom id to element
        valid_ids: Dict[int, tuple[Any, List[int]]]= {}
        ellipses_in_doc = self.svg.xpath('//svg:ellipse', namespaces=inkex.NSS)

        for el in ellipses_in_doc:
            element_id, neighbors = self.parse_point_id(el.get('id'))
            if element_id:
                valid_ids[element_id] = el, neighbors

        # breakpoint()
        # Clean lines
        if clean_lines:
            for line in layer.findall('.//svg:line', namespaces=inkex.NSS):
                a_id = line.get('flutter_maps:a_id')
                b_id = line.get('flutter_maps:b_id')

                # Skip lines that don't have flutter_maps attributes
                if a_id is None and b_id is None:
                    continue

                # Remove or clean lines that reference non-existent points
                a_present= int(a_id) in valid_ids if a_id else False
                b_present= int(b_id) in valid_ids if b_id else False

                if not a_present or not b_present:
                    # self.msg(f"Removing orphan line connecting A:{a_id} B:{b_id}. Line ID was {line.get('id')}.")
                    layer.remove(line)

        # Clean neighbors in point IDs
        for custom_id, (el, linked_ids_list) in valid_ids.items():

            element_id = el.get('id')

            # Keep only neighbors that exist
            cleaned_neighbors = [str(n) for n in linked_ids_list if n in valid_ids]
            if len(cleaned_neighbors) < len(linked_ids_list):
                # self.msg(f"Updating neighbors for point ID {element_id}: {neighbors} -> {cleaned_neighbors}")
                # breakpoint()
                new_id_attr = self.build_point_id_attr(custom_id, cleaned_neighbors)
                el.set('id', new_id_attr)

    document_buildings = None
    unique_entrances_ids = None

    def is_building_point(self, element) -> bool:
        id_attr = element.get('id')
        assert id_attr is not None, "Element has no ID attribute"
        
        point_id = self.get_point_id_number(id_attr)
        assert point_id is not None, f"Point ID could not be extracted from element ID: {id_attr}"

        if self.document_buildings is None:
            self.document_buildings = [e for e in self.svg.get_ids() if self.BUILDING_ID_REGEX.match(e)]
        
        if self.unique_entrances_ids is None:
            # extract unique entrance IDs from document buildings (we asume each element matches the regex)
            self.unique_entrances_ids = [self.BUILDING_ID_REGEX.match(e).group(4) for e in self.document_buildings] # pyright: ignore[reportOptionalMemberAccess]
        
        if point_id in self.unique_entrances_ids:
            return True

        return False

        
        


    def smart_connect_points(self, smart_connect_type: SmartConnectTypes, **connection_params):
        """ Smart connect points using specified algorithm """
        def smart_connect_nearest_point(ignore_building_point: bool = True, max_radius: str ="0.1px"):
            """ Connect points to the nearest point within a specified radius """
            pass
        
        # TODO: Validate and process inputs

        if smart_connect_type == self.SmartConnectTypes.NEAREST_POINT:
            smart_connect_nearest_point(**connection_params)
        else:
            raise NotImplementedError(f'Smart connect type not implemented: {smart_connect_type}')


    from dataclasses import dataclass
    @dataclass
    class PointInfo:
        """ DTO class used to wrap a point's svg element and required info for connection operations """
        el: inkex.elements.BaseElement
        id: str
        neighbors: Union[List[int], List[str]]
    
    @dataclass
    class BuildingInfo:
        """ DTO class used to wrap a building's svg element and required info for connection operations """
        el: inkex.elements.BaseElement
        id: str
        type: str
        subtype: Union[str, None]
        entrance_ids: Union[List[int], List[str]]
        entrance_element: Union[inkex.elements.BaseElement, None]

    def connect_points(self, connection_options: PointConnectionOptions = PointConnectionOptions()):
        # Input Validation: at least 2 selected elements
        selected_elements: selected.ElementList = self.svg.selected
        if not selected_elements or len(selected_elements) <= 0:
            raise inkex.AbortExtension("No selection: Need to select at least 2 objects")

        # Input Filtering: ellipses and circles only (elipse for connection points and circles for entrances)
        # NOTE: selected_elements holds the elements in the user selection order
        selected_ellipses: List = list(selected_elements.filter(polygons.Ellipse)) + list(selected_elements.filter(polygons.Circle))

        # Input Validation: at least 2 selected ellipses / circles (remaining elements after filtering)
        if len(selected_ellipses) < 2:
            raise inkex.AbortExtension( f"Not enough ellipses selected. Need at least 2, got {len(selected_ellipses)}.")

        # Input Sorting: sort selected elements if specified
        use_reverse_sorting = (connection_options.sort_direction == self.PointConnectionOptions.SortDirection.DESCENDING)

        if connection_options.sort_mode == self.PointConnectionOptions.SortMode.X_AXIS:
            selected_ellipses.sort(key=lambda e: e.bounding_box().center[0], reverse=use_reverse_sorting)
        elif connection_options.sort_mode == self.PointConnectionOptions.SortMode.Y_AXIS: 
            selected_ellipses.sort(key=lambda e: e.bounding_box().center[1], reverse=use_reverse_sorting)

        # Input Normalization: extract and group required information for connection operation

        # create list with entries containing: the element, numeric id & neighbours
        elements_info: List[FlutterMapExtension.PointInfo] = []

        # find max existing model point id across the whole document to assign new IDs
        max_id_number = self.get_max_existing_object_id(self.svg.get_ids(), self.get_point_id_number)

        for element in selected_ellipses:
            id_attr = element.get('id')

            # attempt to extract an already assigned model point id
            element_id, neighbors = self.parse_point_id(id_attr)

            # Assign a new model point id if not already present
            if element_id is None:
                max_id_number = self.get_next_object_id(max_id_number)
                element_id = max_id_number 
            elements_info.append(self.PointInfo(el= element, id= str(element_id), neighbors= neighbors))
            

        # helper to add point neighbours to an element-point (no duplicates, not the same point as neighbour)
        def add_neighbour(element_info: FlutterMapExtension.PointInfo, neighbor_id: str):  
            """ Takes an element infor dictionary and modifies the state of its contained element to add a new point neighbour"""
            if neighbor_id == element_info.id:
                return
            if neighbor_id not in element_info.neighbors:
                element_info.neighbors.append(neighbor_id) # type: ignore


        # connect consecutive pairs in selection order
        for i in range(len(elements_info) - 1):
            # end condition to avoid index error (no more points available to link)
            if i + 1 >= len(elements_info):
                alert(f'No more objects to link. {i=}')

            A = elements_info[i]
            B = elements_info[i + 1]

            # include each other as neighbors 
            add_neighbour(A, B.id)
            add_neighbour(B, A.id)

            # read coordinates from cx/cy (strip units)
            ax = (A.el.get('cx'))
            ay = (A.el.get('cy'))
            bx = (B.el.get('cx'))
            by = (B.el.get('cy'))

            # parse transforms (identity if missing)
            t_a = inkex.Transform(A.el.get('transform') or '')
            t_b = inkex.Transform(B.el.get('transform') or '')

            # apply transforms according to option
            copy_transform = connection_options.copy_transform
            if copy_transform == 'copy_from_a':
                start = t_a.apply_to_point((ax, ay))
                end   = [bx, by]
            elif copy_transform == 'copy_from_b':
                start = [ax, ay]
                end   = t_b.apply_to_point((bx, by))
            elif copy_transform == 'copy_from_both':
                start = t_a.apply_to_point((ax, ay))
                end   = t_b.apply_to_point((bx, by))
            else:  # no_copy
                start = [ax, ay]
                end   = [bx, by]

            # create svg line element
            line = polygons.PathElement.new(f"M {start[0]},{start[1]} L {end[0]},{end[1]}")

            # keep style simple; users can edit stroke later in Inkscape
            line.style['stroke'] = connection_options.line_color
            line.style['stroke-width']= connection_options.lines_stroke
            line.set('flutter_maps:modified_by_code', 'inkscape_extension')
            line.set('flutter_maps:a_id', str(A.id))
            line.set('flutter_maps:b_id', str(B.id))
            line.set('id', f'nav_line-{line.get("flutter_maps:a_id")}-{line.get("flutter_maps:b_id")}')

            # set z-order 1 level below points z-order
            if connection_options.draw_lines: 
                # Check if there is a "points" layer in the document, otherwise create it
                # Then add the entrance point to that layer that we avoid any transform issues with the current layer
                query = '//svg:g[@inkscape:groupmode="layer" and @inkscape:label="navigation"]'
                layers_search_result = self.svg.xpath(query)

                if layers_search_result:
                    points_layer = layers_search_result[0]

                else:
                    # Create it if it doesn't exist
                    points_layer = inkex.Layer.new("navigation")
                    self.svg.add(points_layer)

                # MOVE the layer to the very bottom of the XML tree (Top Z-index)
                # Even if it already existed elsewhere, this moves it to the end.
                self.svg.append(points_layer)

                # Add line to points layer (at the end, so on top of other svg objects but behind points)
                points_layer.insert(0, line)

        # Update element IDs with neighbors
        for info in elements_info:
            # sort neighbors to keep deterministic order (optional)
            # keep insertion order for closer match to behavior; but uniqueness enforced.
            neighbors = info.neighbors
            id_val = self.build_point_id_attr(info.id, neighbors)
            info.el.set('id', id_val)
   
    def get_displacement_entrance_coordinates(
        self,
        entrance_x: float,
        entrance_y: float,
        building_bbox: inkex.BoundingBox,
        entrance_bbox: inkex.BoundingBox,
        point_position: 'FlutterMapExtension.BuildingOptions.PointPosition',
        separation_type: 'FlutterMapExtension.BuildingOptions.PointToBorderSeparation',
        custom_separation: Union[str, None] = None,
    ) -> tuple[float, float]:
        """
        Calculates the displaced entrance coordinates based on the specified separation type.

        :param entrance_x: Original x-coordinate of the entrance.
        :param entrance_y: Original y-coordinate of the entrance.
        :param building_bbox: Bounding box of the building.
        :param entrance_bbox: Bounding box of the entrance.
        :param separation_type: Type of separation to apply.
        :param custom_separation: Custom separation value if applicable.

        :return: Tuple containing the new x and y coordinates of the entrance.
        """

        building_options = self.BuildingOptions

        # Extract building borders
        building = {
            "left":   building_bbox.left,
            "right":  building_bbox.right,
            "top":    building_bbox.top,
            "bottom": building_bbox.bottom,
            "w":      building_bbox.width,
            "h":      building_bbox.height,
        }

        # Extract entrance borders
        entrance = {
            "left":   entrance_bbox.left,
            "right":  entrance_bbox.right,
            "top":    entrance_bbox.top,
            "bottom": entrance_bbox.bottom,
            "w":      entrance_bbox.width,
            "h":      entrance_bbox.height,
        }

        # --------- HELPERS ------------------------------------------------------

        def border_to_border_in_displacement():
            if point_position in (
                building_options.PointPosition.UPPER_LEFT,
                building_options.PointPosition.CENTER_LEFT,
                building_options.PointPosition.LOWER_LEFT,
            ):
                return building["left"] - entrance["left"], 0

            if point_position in (
                building_options.PointPosition.UPPER_RIGHT,
                building_options.PointPosition.CENTER_RIGHT,
                building_options.PointPosition.LOWER_RIGHT,
            ):
                return building["right"] - entrance["right"], 0

            if point_position == building_options.PointPosition.UPPER_CENTER:
                return 0, building["top"] - entrance["top"]

            if point_position == building_options.PointPosition.LOWER_CENTER:
                return 0, building["bottom"] - entrance["bottom"]

            return 0, 0

        def border_to_border_out_displacement():
            if point_position in (
                building_options.PointPosition.UPPER_LEFT,
                building_options.PointPosition.CENTER_LEFT,
                building_options.PointPosition.LOWER_LEFT,
            ):
                return building["left"] - entrance["right"], 0

            if point_position in (
                building_options.PointPosition.UPPER_RIGHT,
                building_options.PointPosition.CENTER_RIGHT,
                building_options.PointPosition.LOWER_RIGHT,
            ):
                return building["right"] - entrance["left"], 0

            if point_position == building_options.PointPosition.UPPER_CENTER:
                return 0, building["top"] - entrance["bottom"]

            if point_position == building_options.PointPosition.LOWER_CENTER:
                return 0, building["bottom"] - entrance["top"]

            return 0, 0

        def ten_percent_direction_vector(outside: bool):
            # Sign depends on OUT vs IN
            mult = 1 if outside else -1

            # Horizontal
            if point_position in ( 
                building_options.PointPosition.UPPER_LEFT,
                building_options.PointPosition.CENTER_LEFT,
                building_options.PointPosition.LOWER_LEFT):
                dx = -0.1 * building["w"] * mult
            elif point_position in (
                building_options.PointPosition.UPPER_RIGHT,
                building_options.PointPosition.CENTER_RIGHT,
                building_options.PointPosition.LOWER_RIGHT,
            ):
                dx = 0.1 * building["w"] * mult
            else:
                dx = 0

            # Vertical
            if point_position in (
                building_options.PointPosition.UPPER_LEFT,
                building_options.PointPosition.UPPER_CENTER,
                building_options.PointPosition.UPPER_RIGHT,
            ):
                dy = -0.1 * building["h"] * mult
            elif point_position in (
                building_options.PointPosition.LOWER_LEFT,
                building_options.PointPosition.LOWER_CENTER,
                building_options.PointPosition.LOWER_RIGHT,
            ):
                dy = 0.1 * building["h"] * mult
            else:
                dy = 0

            return dx, dy

        # --------- MAIN LOGIC ---------------------------------------------------

        if point_position == building_options.PointPosition.CENTER:  # Center position, no separation adjustment needed
            return entrance_x, entrance_y

        if separation_type == building_options.PointToBorderSeparation.BORDER_TO_BORDER_IN:
            dx, dy = border_to_border_in_displacement()

        elif separation_type == building_options.PointToBorderSeparation.BORDER_TO_BORDER_OUT:
            dx, dy = border_to_border_out_displacement()

        elif separation_type == building_options.PointToBorderSeparation.TEN_PERCENT_TO_BORDER_IN:
            # Inside the building, 10% displaced from the the border
            base_dx, base_dy = border_to_border_in_displacement()
            extra_dx, extra_dy = ten_percent_direction_vector(outside=False)
            dx, dy = base_dx + extra_dx, base_dy + extra_dy

        elif separation_type == building_options.PointToBorderSeparation.TEN_PERCENT_TO_BORDER_OUT:
            # Outside the building, 10% displaced from the the border
            base_dx, base_dy = border_to_border_out_displacement()
            extra_dx, extra_dy = ten_percent_direction_vector(outside=True)
            dx, dy = base_dx + extra_dx, base_dy + extra_dy

        elif separation_type == building_options.PointToBorderSeparation.CUSTOM:
            raise NotImplementedError('Custom point separation not implemented yet.')
        else:
            raise ValueError(f'Unknown separation type: {separation_type}')

        return dx, dy
                   

    def add_building(self, building_options: BuildingOptions = BuildingOptions(), sort_mode: str ='no_sort', 
                     sort_direction: str ='asc', entrance_point_options: EntrancePointOptions = EntrancePointOptions()):
        """
        Adds a building element to the map at a specified location with given properties.

        """

        selected_elements: selected.ElementList = self.svg.selected
        if not selected_elements or len(selected_elements) <= 0:
            raise inkex.AbortExtension("No selection: Need to select at least 2 objects")
            
        # get selected objects in selection order
        selected_objects: List = list(selected_elements)

        if len(selected_objects) < 2:
            raise inkex.AbortExtension( f"Not enough objects selected. Need at least 2, got {len(selected_objects)}.")

        use_reverse_sorting = (sort_direction == 'desc')
        if sort_mode == 'sort_horizontally':
            selected_objects.sort(key=lambda e: e.bounding_box().center[0], reverse=use_reverse_sorting)

        elif sort_mode == 'sort_vertically':
            selected_objects.sort(key=lambda e: e.bounding_box().center[1], reverse=use_reverse_sorting)

        # find max existing building-N index across the whole document to assign new IDs
        max_id_number = 0
        for id in self.svg.get_ids():
            matches = self.BUILDING_ID_REGEX.match(id)

            if not matches: 
                continue  # skip non-matching ids

            # altough there is an optional building subtype, the group index for numeric will always be group 3
            id_number = int(matches.group(3))
            if id_number > max_id_number:
                max_id_number = id_number


        # create list with entries containing: the element, numeric id & neighbours
        elem_info: List[FlutterMapExtension.BuildingInfo] = []
        for element in selected_objects:
            id_attr = element.get('id')
            # remove elements that are flutter-map points, if we find any likely means that some of the buildings are already linked to a point, we can later retrieve that 
            # point elemnent if required using the building's entrances_ids 
            if self.POINT_ID_REGEX.match(id_attr):
                continue

            building_type, building_subtype, building_id, entrances_ids = self.parse_building_id(id_attr)

            # if no element id, means this element has not been designated as building yet, so we add relevant info
            if building_id is None:
                # assign new id
                max_id_number = self.get_next_object_id(max_id_number)
                building_id = max_id_number 
                # building_options.custom_type will be None unless building type is custom and building_options.building_type == BuildingOptions.BuildingType.CUSTOM
                building_type = building_options.custom_type if building_options.custom_type else building_options.building_type.value # type: ignore
                # building_options.custom_subtype will be None / ignored unless building type is custom, instead we use the 
                # default subtype from the default building type if applicable (e.g., toilet-male, toilet-female, etc)
                building_subtype: Union[str, None] = building_options.custom_subtype if building_options.custom_type else building_options.building_type.value.split('-')[1] if '-' in building_options.building_type.value else None # type: ignore
            else: 
                # TODO: Decide if we want to update existing building types/subtypes based on current options, or we dont process them
                continue

            # if no entrances_ids, means this building has no connection point yet

            elem_info.append(self.BuildingInfo(el= element, type= building_type, subtype= building_subtype, 
                              id= str(building_id), entrance_ids= entrances_ids, entrance_element=None))
        


        layer = self.svg.get_current_layer()
        # Now we procceed to determine the atributes for each building and create their associated connnection point if expecified, 
        # We have already filtered flutter-map points from elem_info so we only have buildings to process


        last_created_point_id_number = None
        for building_info in elem_info:

            # we will: 
            # 1. get / create the building connection point (entrance)
            # 2. determine the entrance coordinates based on building bounding box and options
            # 3. Add the relationship between building and entrance point (adding entrance id to building id attribute). Poitn will not have building id in its id attribute.
            # 4. create and draw the point / entrance svg element if required
            # 5. Finally, update the building & point elements id attributes (inkex does not automatically update them due to performance reasons)

            building_element = building_info.el
            building_id = building_info.id
            building_subtype = building_info.subtype
            building_type = building_info.type
            entrances_ids = building_info.entrance_ids
            
            should_create_entrance_point = building_options.add_connection_point

            if len(entrances_ids) > 0:
                self.msg(f'Building ID {building_id} already has entrance points defined: {entrances_ids}. Skipping entrance point creation.')
                should_create_entrance_point = False
            
            
            if should_create_entrance_point:
                # Get next available point ID, (takes into account ids that may have been created in previous iterations)
                max_point_id_number = last_created_point_id_number if last_created_point_id_number \
                    else self.get_max_existing_object_id(self.svg.get_ids(), self.get_point_id_number)
                next_point_id = self.get_next_object_id(max_point_id_number)

                # 1. Determine entrance position based on building bounding box
                bbox = building_element.bounding_box()
                if bbox is None:
                    self.msg(f'Warning: Could not get bounding box for building {building_id}. Skipping entrance creation.')
                    continue
                    
                # Calculate entrance position based on building options. 

                point_position = building_options.building_point_position  # Point position will always be defined if should_create_entrance_point is True

                if point_position == building_options.PointPosition.LOWER_CENTER:
                    entrance_x = (bbox.left + bbox.right) / 2
                    entrance_y = bbox.bottom 

                elif point_position == building_options.PointPosition.LOWER_LEFT:
                    entrance_x = bbox.left
                    entrance_y = bbox.bottom
                    
                elif point_position == building_options.PointPosition.LOWER_RIGHT:
                    entrance_x = bbox.right
                    entrance_y = bbox.bottom
                    
                elif point_position == building_options.PointPosition.CENTER:
                    entrance_x = (bbox.left + bbox.right) / 2
                    entrance_y = (bbox.top + bbox.bottom) / 2
                    
                elif point_position == building_options.PointPosition.CENTER_LEFT:
                    entrance_x = bbox.left
                    entrance_y = (bbox.top + bbox.bottom) / 2
                    
                elif point_position == building_options.PointPosition.CENTER_RIGHT:
                    entrance_x = bbox.right
                    entrance_y = (bbox.top + bbox.bottom) / 2
                    
                elif point_position == building_options.PointPosition.UPPER_CENTER:
                    entrance_x = (bbox.left + bbox.right) / 2
                    entrance_y = bbox.top
                    
                elif point_position == building_options.PointPosition.UPPER_LEFT:
                    entrance_x = bbox.left 
                    entrance_y = bbox.top 
                    
                elif point_position == building_options.PointPosition.UPPER_RIGHT:
                    entrance_x = bbox.right
                    entrance_y = bbox.top

                else:  # Default to center if unknown
                    self.msg(f'Warning: Unhandled entrance position {point_position}, aboring...')
                    raise inkex.AbortExtension(f'Unhandled entrance position {point_position} for building {building_id}')
                            
                # 2. Create the entrance point SVG element
                entrance_element = polygons.Circle.new(
                    center= (entrance_x, entrance_y),
                    radius=entrance_point_options.point_radius # Allow configuring entrance point radius via building options
                )

                
                # 3. Move the entrance point according to separation options
                bbox_entrance = entrance_element.bounding_box()  # Force bbox calculation
                assert bbox_entrance is not None, "Entrance bounding box could not be determined after creation."

                separation_type = building_options.point_to_border_separation
                assert separation_type is not None, "Separation type must be defined when creating entrance point."


                entrance_dx, entrance_dy= self.get_displacement_entrance_coordinates(      
                    entrance_x, entrance_y,
                    bbox,
                    bbox_entrance,
                    point_position,
                    separation_type,
                    building_options.custom_point_separation
                )
                from inkex import Transform
                            
                # Set entrance point metadata
                entrance_element.set('flutter_maps:type', 'point')
                entrance_element.set('flutter_maps:subtype', 'entrance')
                entrance_element.set('flutter_maps:building_id', building_id)
                entrance_element.set('flutter_maps:modified_by_code', 'inkscape_extension')

                # Style the entrance point based on specified options
                entrance_element.style['fill'] = entrance_point_options.point_fill_color
                entrance_element.style['stroke'] = entrance_point_options.point_stroke_color
                entrance_element.style['stroke-width'] = entrance_point_options.point_stroke
                
                # Add entrance point to the building's neighbours
                entrances_ids.append(next_point_id)
                building_info.entrance_ids = entrances_ids
                                    
                # store the entrance element for later use
                building_info.entrance_element = entrance_element
                self.msg(f'Created entrance point {next_point_id} for building {building_id} at ({entrance_x:.2f}, {entrance_y:.2f})')
            
                # Update building element's ID attribute with entrance relationships
                entrance_ids = building_info.entrance_ids
                # Create the ID attribute string in format: 
                building_id_val = self.build_building_id_attr(
                    building_type=building_type,
                    building_subtype=building_subtype,
                    id=int(building_id),
                    entrance_ids=entrance_ids # type: ignore
                )

                # Insert the entrance point into the SVG
                if should_create_entrance_point:

                    last_created_point_id_number = next_point_id

                    # Update the selected object id so that it is now a building with a linked point (entrance)
                    building_info.el.set('id', building_id_val)  

                    entrance_element.set('inkscape:label', f'building_point:{building_id}')

                    # Set the point id (will not be linked to building id, the building is the only one that links to the point)
                    entrance_id_val = self.build_point_id_attr(
                        id=str(next_point_id),
                        neighbors_list=[]
                    )

                    # entrance element will never be null (its created programatically)
                    building_info.entrance_element.set('id', entrance_id_val) # type: ignore

                    # Check if there is a "points" layer in the document, otherwise create it
                    # Then add the entrance point to that layer so we avoid any transform issues with the current layer
                    query = '//svg:g[@inkscape:groupmode="layer" and @inkscape:label="navigation"]'
                    layers_search_result = self.svg.xpath(query)

                    if layers_search_result:
                        points_layer = layers_search_result[0]

                    else:
                        # Create it if it doesn't exist
                        points_layer = inkex.Layer.new("navigation")
                        self.svg.add(points_layer)

                    # MOVE the layer to the very bottom of the XML tree (Top Z-index)
                    # Even if it already existed elsewhere, this moves it to the end.
                    self.svg.append(points_layer)

                    # We proceed to normalize the cordinates to obtain the final x and y poisitioning for the points layer 
                    
                    # 1. Use the parent's composed transform (since bbox was in parent space)
                    # This prevents the "double-scaling"
                    parent_matrix = building_element.getparent().composed_transform()

                    # 2. Use the exact points calculated earlier (Position + Displacement)
                    # We use Vector2d to ensure accurate point-wise math.
                    final_local_pt = inkex.Vector2d(entrance_x + entrance_dx, entrance_y + entrance_dy)
                    global_pos = parent_matrix.apply_to_point(final_local_pt)

                    # 3. Calculate the coordinate relative to the "points" layer
                    points_layer_transform = points_layer.composed_transform()
                    local_target = (-points_layer_transform).apply_to_point(global_pos)

                    # 4. Set the entrance_element position and CLEAR its transform
                    # We clear the transform because the displacement is now baked into cx/cy.
                    entrance_element.set('cx', str(local_target.x))
                    entrance_element.set('cy', str(local_target.y))
                    entrance_element.transform = None 

                    # 5. Add to the layer
                    points_layer.add(entrance_element)


if __name__ == '__main__':
    try:
        import inkscape_ExtensionDevTools 
        inkscape_ExtensionDevTools.inkscape_run_debug()
    except Exception as e :
        alert(f'something happened when executing extension Dev Tools: {e}' )
    
    FlutterMapExtension().run()
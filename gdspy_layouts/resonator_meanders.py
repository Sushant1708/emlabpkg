import numpy as np
import gdspy

class HangerConfiguration:
    def __init__(self, path_width, path3_width, gap, inner_angle, length_of_one_segment, total_loops, padding=40, 
                 rotation_angle=0, layers=[0, 1], points=43, x=0, y=0, first_seg_length=None, coupler_length=None, 
                 want_feedline_and_pads=False, feedline_extend_length=0, feedline_width=0, feedline_path_width=0,
                 coupler_gap=0):
        self.path_width = path_width
        self.path3_width = path3_width
        self.gap = gap
        self.inner_angle = inner_angle
        self.length_of_one_segment = length_of_one_segment
        self.total_loops = total_loops
        self.padding = padding
        self.rotation_angle = rotation_angle
        self.layers = layers
        self.points = points
        self.x = x
        self.y = y
        self.first_seg_length = first_seg_length
        self.coupler_length = coupler_length
        self.want_feedline_and_pads = want_feedline_and_pads
        self.feedline_extend_length = feedline_extend_length
        self.feedline_width = feedline_width
        self.feedline_path_width = feedline_path_width
        self.coupler_gap = coupler_gap
        self.outer_angle = self.inner_angle + self.gap + self.path_width

class HangerArrayConfiguration:
    def __init__(self, config, num_hangers_bottom, num_hangers_top, distance_between_meanders=100, feedline_width=50, feedline_path_width=15, feedline_extend_length=100, x_dist_pad_from_feedline=100):
        if isinstance(config, list):
            if len(config) == 2:
                if len(config[0]) == num_hangers_bottom and len(config[1]) == num_hangers_top:
                    self.configs = config
                elif len(config[0]) == 1 and len(config[1]) == 1:
                    self.configs = [config[0] * num_hangers_bottom, config[1] * num_hangers_top]
                else:
                    raise AttributeError("Length of the sublists of config objects should match the number of resonators.")
            else:
                raise AttributeError("The outer list should have exactly 2 sublists for top and bottom resonators.")
        elif isinstance(config, HangerConfiguration):
            self.configs = [[config] * num_hangers_bottom, [config] * num_hangers_top]
        
        for config_list in self.configs:
            for config in config_list:
                if config.want_feedline_and_pads:
                    raise AttributeError("The configurator passed to this function cannot have 'want_feedline_and_pads' set to True.")
        
        self.x_dist_pad_from_feedline = x_dist_pad_from_feedline
        self.num_hangers_top = num_hangers_top
        self.num_hangers_bottom = num_hangers_bottom
        self.feedline_width = feedline_width
        self.feedline_path_width = feedline_path_width
        self.feedline_extend_length = feedline_extend_length
        self.distance_between_meanders = distance_between_meanders

class TransmissionConfiguration:
    def __init__(self, path_width, path3_width, gap, inner_angle, length_of_one_segment, total_loops, padding=40, rotation_angle=0, layers=[0, 1], points=43,
                 x=0, y=0, first_seg_length=None, last_seg_length=None, want_touch_pads=False):
        self.path_width = path_width
        self.path3_width = path3_width
        self.gap = gap
        self.inner_angle = inner_angle
        self.length_of_one_segment = length_of_one_segment
        self.total_loops = total_loops
        self.padding = padding
        self.rotation_angle = rotation_angle
        self.layers = layers
        self.points = points
        self.x = x
        self.y = y
        self.first_seg_length = first_seg_length
        self.last_seg_length = last_seg_length
        self.want_touch_pads = want_touch_pads
        self.outer_angle = self.inner_angle + self.gap + self.path_width

class HoleConfiguration:
    def __init__(self, radius=5, x_min=None, x_max=None, y_min=None, y_max=None, path1=None, path2=None, path3s=None,
                write_area=None):
        
        self.radius = radius
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.path1 = path1
        self.path2 = path2
        self.path3s = path3s
        self.write_area = write_area
        self.hole_periods = []

def create_1_transmission(meander_config, hole_config=None):
    
    """
    Create a GDSII transmission resonator using the specified configurator.

    This function generates a GDSII transmission resonator based on the provided configurator objects.
    The configurator defines the geometry and properties of the transmission resonator. Units are in microns by default.

    Parameters:
        configurator (TransmissionResonatorConfigurator): An instance of the TransmissionResonatorConfigurator
            class that defines the configuration for the transmission resonator.
        hole_configurator (HoleConfiguration): An instance of the HoleConfiguration class that defines the configuration
            for the holes around the resonator meander. This should contain the radius of the holes.

    Returns:
        tuple: A tuple containing three GDSII Path objects representing the transmission resonator paths,
        if touch pads are included, two GDSII Polygon objects for the touch pads and, if holes are included, all GDSII
        Circle objects.
    """
    
    path_width = meander_config.path_width
    path3_width = meander_config.path3_width
    gap = meander_config.gap
    inner_angle = meander_config.inner_angle
    length_of_one_segment = meander_config.length_of_one_segment
    total_loops = meander_config.total_loops
    padding = meander_config.padding
    rotation_angle = meander_config.rotation_angle
    layers = meander_config.layers
    points = meander_config.points
    x = meander_config.x
    y = meander_config.y
    first_seg_length = meander_config.first_seg_length
    last_seg_length = meander_config.last_seg_length
    want_touch_pads = meander_config.want_touch_pads
    outer_angle = meander_config.outer_angle
    want_holes = hole_config is not None
    
    if first_seg_length is None:
        first_seg_length = 0.8 * length_of_one_segment
    if last_seg_length is None:
        last_seg_length = 0.8 * length_of_one_segment

    loops_after_one = total_loops - 2

    path1 = gdspy.Path(path_width, (0, 0))
    path2 = gdspy.Path(path_width, (path_width + gap, 0))
    path3 = gdspy.Path(path3_width, ((path_width + gap) / 2, (-padding)))

    path1.segment(40, "+y", layer=layers[0])
    path1.turn(outer_angle, "r", number_of_points=points, layer=layers[0])
    path1.segment(first_seg_length , "+x", layer=layers[0])
    path1.turn(inner_angle, "ll", number_of_points=points, layer=layers[0])
    path1.segment(length_of_one_segment, "-x", layer=layers[0])
    path1.turn(outer_angle, "rr", number_of_points=points, layer=layers[0])
    for i in range(loops_after_one):
        path1.segment(length_of_one_segment, "+x", layer=layers[0])
        path1.turn(inner_angle, "ll", number_of_points=points, layer=layers[0])
        path1.segment(length_of_one_segment, "-x", layer=layers[0])
        path1.turn(outer_angle, "rr", number_of_points=points)
    path1.segment(length_of_one_segment, "+x", layer=layers[0])
    path1.turn(inner_angle, "ll", number_of_points=points, layer=layers[0])
    path1.segment(last_seg_length, "-x", layer=layers[0])
    path1.turn(outer_angle, "r", number_of_points=points, layer=layers[0])
    path1.segment(40, "+y", layer=layers[0])

    path2.segment(40, "+y", layer=layers[0])
    path2.turn(inner_angle, "r", number_of_points=points, layer=layers[0])
    path2.segment(first_seg_length, "+x", layer=layers[0])
    path2.turn(outer_angle, "ll", number_of_points=points, layer=layers[0])
    path2.segment(length_of_one_segment, "-x", layer=layers[0])
    path2.turn(inner_angle, "rr", number_of_points=points, layer=layers[0])
    for i in range(loops_after_one):
        path2.segment(length_of_one_segment, "+x", layer=layers[0])
        path2.turn(outer_angle, "ll", number_of_points=points, layer=layers[0])
        path2.segment(length_of_one_segment, "-x", layer=layers[0])
        path2.turn(inner_angle, "rr", number_of_points=points, layer=layers[0])
    path2.segment(length_of_one_segment, "+x", layer=layers[0])
    path2.turn(outer_angle, "ll", number_of_points=points, layer=layers[0])
    path2.segment(last_seg_length, "-x", layer=layers[0])
    path2.turn(inner_angle, "r", number_of_points=points, layer=layers[0])
    path2.segment(40, "+y", layer=layers[0])

    path3.segment(padding + 40, "+y", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "r", layer=layers[1])
    path3.segment(first_seg_length, "+x", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "ll", layer=layers[1])
    path3.segment(length_of_one_segment, "-x", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "rr", layer=layers[1])
    for i in range(loops_after_one):
        path3.segment(length_of_one_segment, "+x", layer=layers[1])
        path3.turn((inner_angle + outer_angle) / 2, "ll", layer=layers[1])
        path3.segment(length_of_one_segment, "-x", layer=layers[1])
        path3.turn((inner_angle + outer_angle) / 2, "rr", layer=layers[1])
    path3.segment(length_of_one_segment, "+x", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "ll", layer=layers[1])
    path3.segment(last_seg_length, "-x", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "r", layer=layers[1])
    path3.segment(padding + 40, "+y", layer=layers[1])

    if want_touch_pads:
        pad1 = make_touch_pad_for_transmission_resonator(path1, path2, '+y')
        pad2 = make_touch_pad_for_transmission_resonator(path1, path2, '-y')
        
        all_vertices_pad3 = np.vstack(pad1.polygons)
        points = [[np.min(all_vertices_pad3[:, 0]) - padding, np.min(all_vertices_pad3[:, 1]) - padding], 
                  [np.min(all_vertices_pad3[:, 0]) - padding, np.max(all_vertices_pad3[:, 1]) + padding],
                  [np.max(all_vertices_pad3[:, 0]) + padding, np.max(all_vertices_pad3[:, 1]) + padding],
                  [np.max(all_vertices_pad3[:, 0]) + padding, np.min(all_vertices_pad3[:, 1]) - padding]]
        pad3 = gdspy.Polygon(points=points, layer=1)
        
        all_vertices_pad4 = np.vstack(pad2.polygons)
        points = [[np.min(all_vertices_pad4[:, 0]) - padding, np.min(all_vertices_pad4[:, 1]) - padding], 
                  [np.min(all_vertices_pad4[:, 0]) - padding, np.max(all_vertices_pad4[:, 1]) + padding],
                  [np.max(all_vertices_pad4[:, 0]) + padding, np.max(all_vertices_pad4[:, 1]) + padding], 
                  [np.max(all_vertices_pad4[:, 0]) + padding, np.min(all_vertices_pad4[:, 1]) - padding]]
        pad4 = gdspy.Polygon(points=points, layer=1)

        path1.rotate(rotation_angle, center=(x, y))
        path2.rotate(rotation_angle, center=(x, y))
        path3.rotate(rotation_angle, center=(x, y))
        pad1.rotate(rotation_angle, center=(x, y))
        pad2.rotate(rotation_angle, center=(x, y))

        objs = [path1, path2, path3, pad1, pad2]

    else:
        path1.rotate(rotation_angle, center=(x, y))
        path2.rotate(rotation_angle, center=(x, y))
        path3.rotate(rotation_angle, center=(x, y))
        
        objs = [path1, path2, path3]
        
    if want_holes:
        
        all_vertices = np.vstack(path3.polygons)
        
        if not want_touch_pads:
            if hole_config.x_min is None:
                hole_config.x_min = int(np.min(all_vertices[:, 0]))
            if hole_config.x_max is None:
                hole_config.x_max = int(np.max(all_vertices[:, 0]))
            if hole_config.y_min is None:
                hole_config.y_min = int(np.min(all_vertices[:, 1]))
            if hole_config.y_max is None:
                hole_config.y_max = int(np.max(all_vertices[:, 1]))
        
        elif want_touch_pads:
            if hole_config.x_min is None:
                hole_config.x_min = int(np.min(all_vertices[:, 0]))
            if hole_config.x_max is None:
                hole_config.x_max = int(np.max(all_vertices[:, 0]))
            if hole_config.y_min is None:
                hole_config.y_min = int(np.min(all_vertices_pad3[:, 1]))
            if hole_config.y_max is None:
                hole_config.y_max = int(np.max(all_vertices_pad4[:, 1]))
            
        hole_config.path1 = path1
        hole_config.path2 = path2
        
        if want_touch_pads:
            hole_config.path3s = [path3, pad3, pad4]
        else:
            hole_config.path3s = [path3]
        
        holes = create_holes(meander_config=meander_config, hole_config=hole_config)
        
        box = gdspy.Polygon(points=[[hole_config.x_min, hole_config.y_min], [hole_config.x_max, hole_config.y_min],
                                   [hole_config.x_max, hole_config.y_max], [hole_config.x_min, hole_config.y_max]])
        
        hole_config.write_area = box
        
        objs.append(holes)
        
    return objs
    
def create_1_hanger(config):
    """
    THIS IS AN OLD FUNCTION. USE HANGER ARRAY FUNCTION INSTEAD -> create_hangers_array().
    Create 1 GDSII hanger resonator. Doesn't create touch pads or holes. Returns 3 paths, 2 for the meander and a third one that
    envelops the meander for holes. Units are in microns by default.

    Parameters:
        config (HangerConfiguration): An instance of HangerConfiguration class that contains configuration parameters.

    Returns:
        tuple: A tuple containing three GDSII Path objects representing the hanger paths or three GDSII Path objects and two
        GDSII Polygon objects.

    Example:
        path1, path2, path3 = create_1_hanger(HangerConfiguration(path_width=15, path3_width=95, gap=10, inner_angle=50,
                                              length_of_one_segment=700, total_loops=4, coupler_length=600))
    """

    path_width = config.path_width
    path3_width = config.path3_width
    gap = config.gap
    inner_angle = config.inner_angle
    length_of_one_segment = config.length_of_one_segment
    total_loops = config.total_loops
    padding = config.padding
    rotation_angle = config.rotation_angle
    layers = config.layers
    points = config.points
    x = config.x
    y = config.y
    first_seg_length = config.first_seg_length
    coupler_length = config.coupler_length
    want_feedline_and_pads = config.want_feedline_and_pads
    feedline_extend_length = config.feedline_extend_length
    feedline_width = config.feedline_width
    feedline_path_width = config.feedline_path_width
    coupler_gap = config.coupler_gap
    outer_angle = config.outer_angle

    if first_seg_length is None:
        first_seg_length = 0.95 * length_of_one_segment
    if coupler_length is None:
        coupler_length = 0.95 * length_of_one_segment

    loops_after_one = total_loops - 2
    coupler_gap = coupler_gap - feedline_path_width - path_width

    path1 = gdspy.Path(path_width, (0, path_width + gap))
    path2 = gdspy.Path(path_width, (0, 0))
    path3 = gdspy.Path(path3_width, (-padding, (path_width + gap) / 2))

    path1.segment(first_seg_length, "+x", layer=layers[0])
    path1.turn(inner_angle, "ll", number_of_points=points, layer=layers[0])
    path1.segment(length_of_one_segment, "-x", layer=layers[0])
    path1.turn(outer_angle, "rr", number_of_points=points, layer=layers[0])
    for i in range(loops_after_one):
        path1.segment(length_of_one_segment, "+x", layer=layers[0])
        path1.turn(inner_angle, "ll", number_of_points=points, layer=layers[0])
        path1.segment(length_of_one_segment, "-x", layer=layers[0])
        path1.turn(outer_angle, "rr", number_of_points=points)
    path1.segment(length_of_one_segment, "+x", layer=layers[0])
    path1.turn(inner_angle, "ll", number_of_points=points, layer=layers[0])
    path1.segment(coupler_length, "-x", layer=layers[0])
    path1.turn((gap + path_width) / 2, "rr", number_of_points=points, layer=layers[0])

    path2.segment(first_seg_length, "+x", layer=layers[0])
    path2.turn(outer_angle, "ll", number_of_points=points, layer=layers[0])
    path2.segment(length_of_one_segment, "-x", layer=layers[0])
    path2.turn(inner_angle, "rr", number_of_points=points, layer=layers[0])
    for i in range(loops_after_one):
        path2.segment(length_of_one_segment, "+x", layer=layers[0])
        path2.turn(outer_angle, "ll", number_of_points=points, layer=layers[0])
        path2.segment(length_of_one_segment, "-x", layer=layers[0])
        path2.turn(inner_angle, "rr", number_of_points=points, layer=layers[0])
    path2.segment(length_of_one_segment, "+x", layer=layers[0])
    path2.turn(outer_angle, "ll", number_of_points=points, layer=layers[0])
    path2.segment(coupler_length, "-x", layer=layers[0])

    path3.segment(first_seg_length + padding, "+x", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "ll", layer=layers[1])
    path3.segment(length_of_one_segment, "-x", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "rr", layer=layers[1])
    for i in range(loops_after_one):
        path3.segment(length_of_one_segment, "+x", layer=layers[1])
        path3.turn((inner_angle + outer_angle) / 2, "ll", layer=layers[1])
        path3.segment(length_of_one_segment, "-x", layer=layers[1])
        path3.turn((inner_angle + outer_angle) / 2, "rr", layer=layers[1])
    path3.segment(length_of_one_segment, "+x", layer=layers[1])
    path3.turn((inner_angle + outer_angle) / 2, "ll", layer=layers[1])
    path3.segment(coupler_length + (path_width + gap) / 2 + padding, "-x", layer=layers[1])

    if want_feedline_and_pads:
        y_max = np.max(path2.polygons[-1][:, 1])
        x_max = np.max(path2.polygons[-1][:, 0])
        x_min = np.min(path2.polygons[-1][:, 0])
        
        points_feedline_lower = [[x_min - feedline_extend_length, y_max + coupler_gap], 
                                 [x_max + feedline_extend_length, y_max + coupler_gap],
                                 [x_max + feedline_extend_length, y_max + coupler_gap + feedline_path_width],
                                 [x_min - feedline_extend_length, y_max + coupler_gap + feedline_path_width]]

        points_feedline_upper = [[x_min - feedline_extend_length, y_max + coupler_gap + feedline_width + feedline_path_width], 
                                 [x_max + feedline_extend_length, y_max + coupler_gap + feedline_width + feedline_path_width],
                                 [x_max + feedline_extend_length, y_max + coupler_gap + feedline_path_width + feedline_width + feedline_path_width],
                                 [x_min - feedline_extend_length, y_max + coupler_gap + feedline_path_width + feedline_width + feedline_path_width]]
        
        feedline_lower = gdspy.Polygon(points_feedline_lower)
        feedline_upper = gdspy.Polygon(points_feedline_upper)
        
        all_objs = [path1, path2, path3, feedline_lower, feedline_upper]
        
        for obj in all_objs:
            obj.translate(dx=x, dy=y)
            obj.rotate(rotation_angle, center=(x, y))
        
        return all_objs

    else:
        
        all_objs = [path1, path2, path3]
        
        for obj in all_objs:
            obj.rotate(rotation_angle, center=(x, y))

        return all_objs
    
def create_hangers_array(super_config, hole_config=None):
    
    want_holes = hole_config is not None
    x_dist_pad_from_feedline = super_config.x_dist_pad_from_feedline
    configs = super_config.configs
    num_reson_bottom = len(super_config.configs[0])
    num_reson_top = len(super_config.configs[1])
    
    distance_between_meanders = super_config.distance_between_meanders
    feedline_extend_length = super_config.feedline_extend_length
    feedline_width = super_config.feedline_width
    feedline_path_width = super_config.feedline_path_width
    
    path1s_left = []
    path2s_left = []
    path3s_left = []
    feedlines = []
    pads = []
    masks = []
    
    width_of_paths = []
    all_coupler_gaps1 = [config.coupler_gap for config in configs[0]]
    x_extreme_points = []
    
    all_holes = []
    
    for i in range(num_reson_bottom):
                
        config = configs[0][i]
        
        path1, path2, path3 = create_1_hanger(config)

        all_vertices = np.vstack(path2.polygons)
        x_coordinates = all_vertices[:, 0]
        max_x = np.max(x_coordinates)
        
        all_vertices = np.vstack(path1.polygons)
        x_coordinates = all_vertices[:, 0]
        min_x = np.min(x_coordinates)
        
        width_of_paths.append((np.abs(max_x) + np.abs(min_x)))
        
        if i != 0:
            width = sum(width_of_paths[0 : i])
            dx = width + distance_between_meanders * i
            dy = all_coupler_gaps1[0] - all_coupler_gaps1[i]
            for path in [path1, path2, path3]:
                path.translate(dx, dy)
                
        elif i == 0:
            coupler_gap = all_coupler_gaps1[0] - feedline_path_width - config.path_width
            y_max = np.max(path2.polygons[-1][:, 1])
        
        x_max = np.max(path2.polygons[-1][:, 0])
        x_min = np.min(path2.polygons[-1][:, 0])
        x_extreme_points.append(x_max)
        x_extreme_points.append(x_min)

        path1s_left.append(path1)
        path2s_left.append(path2)
        path3s_left.append(path3)
    
        if want_holes:
        
            all_vertices = np.vstack(path3.polygons)

            hole_config.x_min = int(np.min(all_vertices[:, 0]))
            hole_config.x_max = int(np.max(all_vertices[:, 0]))
            hole_config.y_min = int(np.min(all_vertices[:, 1]))
            hole_config.y_max = int(np.max(all_vertices[:, 1]))
            
            points_meander_mask = [[hole_config.x_min, hole_config.y_min], [hole_config.x_min, hole_config.y_max], 
                                   [hole_config.x_max, hole_config.y_max], [hole_config.x_max, hole_config.y_min]]
            
            meander_mask = gdspy.Polygon(points=points_meander_mask, layer=1)
            masks.append(meander_mask)

            hole_config.path1 = path1
            hole_config.path2 = path2
            hole_config.path3s = [path3]

            holes = create_holes(meander_config=config, hole_config=hole_config)
    
            all_holes.append(holes)
    
    all_coupler_gaps2 = [config.coupler_gap for config in configs[1]]
    for i in range(num_reson_top):
        config = configs[1][i]
        
        path1, path2, path3 = create_1_hanger(config)

        all_vertices = np.vstack(path2s_left[0].polygons)
        x_coordinates = all_vertices[:, 0]
        max_x = np.max(x_coordinates)
        y_coordinates = all_vertices[:, 1]
        max_y = np.max(y_coordinates)
        min_y = np.min(y_coordinates)
        height_of_resonator = max_y - min_y
        
        all_vertices = np.vstack(path1.polygons)
        x_coordinates = all_vertices[:, 0]
        min_x = np.min(x_coordinates)
        
        width_of_paths.append(max_x - min_x)
        
        if i != 0:
            width = sum(width_of_paths[0 : i])
            dx = width + distance_between_meanders * i
            dy = height_of_resonator + 1 * all_coupler_gaps1[0] + all_coupler_gaps2[i] - 2 * config.path_width + feedline_width
            for path in [path1, path2, path3]:
                path.translate(dx, dy)
                
        elif i == 0:
            dx = 0
            dy = height_of_resonator + all_coupler_gaps1[0] + all_coupler_gaps2[0] - 2 * config.path_width + feedline_width
            for path in [path1, path2, path3]:
                path.translate(dx, dy)

        path1s_left.append(path1)
        path2s_left.append(path2)
        path3s_left.append(path3)
        
        if want_holes:
        
            all_vertices = np.vstack(path3.polygons)

            hole_config.x_min = int(np.min(all_vertices[:, 0]))
            hole_config.x_max = int(np.max(all_vertices[:, 0]))
            hole_config.y_min = int(np.min(all_vertices[:, 1]))
            hole_config.y_max = int(np.max(all_vertices[:, 1]))
            
            points_meander_mask = [[hole_config.x_min, hole_config.y_min], [hole_config.x_min, hole_config.y_max], 
                                   [hole_config.x_max, hole_config.y_max], [hole_config.x_max, hole_config.y_min]]
            
            meander_mask = gdspy.Polygon(points=points_meander_mask, layer=1)
            masks.append(meander_mask)

            hole_config.path1 = path1
            hole_config.path2 = path2
            hole_config.path3s = [path3]

            holes = create_holes(meander_config=config, hole_config=hole_config)
    
            all_holes.append(holes)
    
    x_extreme_points = []
    
    for paths in [path1s_left, path2s_left]:
        for i in range(len(paths)):
            all_vertices = np.vstack(path2s_left[i].polygons)
            x_coordinates = all_vertices[:, 0]
            max_x = np.max(x_coordinates)
            min_x = np.min(x_coordinates)

            x_extreme_points.append(min_x)
            x_extreme_points.append(max_x)
    
    x_min = np.min(x_extreme_points)
    x_max = np.max(x_extreme_points)
    points_feedline_lower = [[x_min - feedline_extend_length, y_max + coupler_gap], 
                             [x_max + feedline_extend_length, y_max + coupler_gap],
                             [x_max + feedline_extend_length, y_max + coupler_gap + feedline_path_width],
                             [x_min - feedline_extend_length, y_max + coupler_gap + feedline_path_width]]

    points_feedline_upper = [[x_min - feedline_extend_length, y_max + coupler_gap + feedline_width + feedline_path_width], 
                             [x_max + feedline_extend_length, y_max + coupler_gap + feedline_width + feedline_path_width],
                             [x_max + feedline_extend_length, y_max + coupler_gap + feedline_path_width + feedline_width + feedline_path_width],
                             [x_min - feedline_extend_length, y_max + coupler_gap + feedline_path_width + feedline_width + feedline_path_width]]
    feedline_lower = gdspy.Polygon(points_feedline_lower)
    feedline_upper = gdspy.Polygon(points_feedline_upper)
    feedlines.append(feedline_lower)
    feedlines.append(feedline_upper)
    
    feedline_mask_lower = gdspy.Polygon(points_feedline_lower)
    feedline_mask_upper = gdspy.Polygon(points_feedline_upper)
    
    pad1 = make_touch_pad_for_feedline(feedline_lower, feedline_upper, "l", length_of_pad=200, width_of_pad=200, thickness_of_pad=50, x_dist_pad_from_feedline=x_dist_pad_from_feedline)
    pad2 = make_touch_pad_for_feedline(feedline_lower, feedline_upper, "r", length_of_pad=200, width_of_pad=200, thickness_of_pad=50, x_dist_pad_from_feedline=x_dist_pad_from_feedline)
    pads.append(pad1)
    pads.append(pad2)
    
    pad1_mask = make_touch_pad_for_feedline(feedline_lower, feedline_upper, "l", length_of_pad=200, width_of_pad=200, thickness_of_pad=50, x_dist_pad_from_feedline=x_dist_pad_from_feedline)
    pad2_mask = make_touch_pad_for_feedline(feedline_lower, feedline_upper, "r", length_of_pad=200, width_of_pad=200, thickness_of_pad=50, x_dist_pad_from_feedline=x_dist_pad_from_feedline)
    
    merged_mask = gdspy.boolean([feedline_mask_lower, feedline_mask_upper], [pad1_mask, pad2_mask], "or")
    
    all_vertices = np.vstack(merged_mask.polygons)
    x_coordinates = all_vertices[:, 0]
    y_coordinates = all_vertices[:, 1]
    min_x = np.min(x_coordinates)
    max_x = np.max(x_coordinates)
    min_y = np.min(y_coordinates)
    max_y = np.max(y_coordinates)
    
    points_for_feedline_pads_mask = [[min_x - 40, min_y - 40], [min_x - 40, max_y + 40], 
                                     [max_x + 40, max_y + 40], [max_x + 40, min_y - 40]]
    
    feedline_pads_mask = gdspy.Polygon(points_for_feedline_pads_mask, layer=1)
    masks.append(feedline_pads_mask)
    
    return [path1s_left, path2s_left, path3s_left, feedlines, pads, masks, all_holes]

def make_touch_pad_for_transmission_resonator(feedline_left, feedline_right, direction, length_of_pad=200, width_of_pad=200, thickness_of_pad=50):
    
    """
    Creates a touch pad for a transmission resonator. Units are in microns by default.

    Parameters:
        feedline_left (gdspy.Path): The left feedline (path1) of the transmission resonator.
        feedline_right (gdspy.Path): The right feedline (path2) of the transmission resonator.
        direction (str): The direction of the transmission line. Either "+y" (upward) or "-y" (downward).
        length_of_pad (float, optional): The length of the touch pad (default is 200 units).
        width_of_pad (float, optional): The width of the touch pad (default is 200 units).
        thickness_of_pad (float, optional): The thickness of the touch pad (default is 50 units).

    Returns:
        gdspy.Polygon: A Polygon object representing the generated touch pad.

    Example:
        # Create a touch pad for a transmission resonator with upward direction
        pad = make_touch_pad_for_transmission_resonator(path1, path2, direction="+y")
    """

    if direction == "+y":
        
        poly1 = feedline_left.polygons[0]
        poly2 = feedline_right.polygons[0]
        
        feedline_width = np.abs(feedline_left.polygons[0][0][0]) + np.abs(feedline_left.polygons[0][1][0])
        diff = thickness_of_pad - feedline_width
        x_constant = 95
        y_constant = 75
        
        points = [poly1[1], poly1[0], poly1[0] - [x_constant + diff, y_constant], 
                  poly1[0] - [x_constant + diff, y_constant + length_of_pad + thickness_of_pad], 
                  poly2[1] + [x_constant + diff, -(y_constant + length_of_pad + thickness_of_pad)], 
                  poly2[1] + [x_constant + diff, -(y_constant)], poly2[1], poly2[0], 
                  poly2[0] + [x_constant, -(y_constant)], poly2[0] + [x_constant, -(y_constant + length_of_pad)], 
                  poly1[1] - [x_constant, y_constant + length_of_pad], poly1[1] - [x_constant, y_constant], poly1[1]]
        pad = gdspy.Polygon(points, layer=0)
        
        return pad
    
    if direction == "-y":
        
        poly1 = feedline_left.polygons[-1]
        poly2 = feedline_right.polygons[-1]
        
        feedline_width = np.abs(feedline_left.polygons[-1][3][0]) + np.abs(feedline_left.polygons[-1][2][0])
        diff = thickness_of_pad - feedline_width
        x_constant = 95
        y_constant = 75 
        
        points = [poly1[2], poly1[3], poly1[3] - [x_constant + diff, -(y_constant)], 
                  poly1[3] - [x_constant + diff, -(y_constant + length_of_pad + thickness_of_pad)], 
                  poly2[2] + [x_constant + diff, (y_constant + length_of_pad + thickness_of_pad)], 
                  poly2[2] + [x_constant + diff, y_constant], poly2[2], poly2[3], poly2[3] + [x_constant, y_constant], 
                  poly2[3] + [x_constant, y_constant + width_of_pad], poly1[2] - [x_constant, -(y_constant + width_of_pad)], 
                  poly1[2] - [x_constant, -(y_constant)], poly1[2]]
        pad = gdspy.Polygon(points, layer=0)
        
        return pad
    
def make_touch_pad_for_feedline(feedline_left, feedline_right, direction, length_of_pad=200, width_of_pad=200, 
                                thickness_of_pad=50, x_dist_pad_from_feedline=100):
    
    if direction == "r":
        
        feedline_lower = feedline_left.polygons[0]
        feedline_higher = feedline_right.polygons[0]
        
        feedline_lower_min_y = np.min(feedline_lower[:, 1])
        feedline_lower_max_y = np.max(feedline_lower[:, 1])
        feedline_higher_min_y = np.min(feedline_higher[:, 1])
        feedline_higher_max_y = np.max(feedline_higher[:, 1])
        max_x = np.max(feedline_lower[:, 0])
        
        feedline_path_width = feedline_lower_max_y - feedline_lower_min_y
        feedline_width = feedline_higher_min_y - feedline_lower_max_y
        diff = thickness_of_pad - feedline_width
        feedline_gap_midpoint = np.mean([feedline_higher_min_y, feedline_lower_max_y])
        
        pad_inner_higher_edge_y = feedline_gap_midpoint + (width_of_pad / 2)
        pad_inner_lower_edge_y = feedline_gap_midpoint - (width_of_pad / 2)
        pad_outer_lower_edge_y = pad_inner_lower_edge_y - thickness_of_pad
        pad_outer_higher_edge_y = pad_inner_higher_edge_y + thickness_of_pad
        
        
        points = [[max_x, feedline_lower_max_y], 
                  [max_x, feedline_lower_min_y], 
                  [max_x + x_dist_pad_from_feedline, pad_outer_lower_edge_y], 
                  [max_x + x_dist_pad_from_feedline + length_of_pad + thickness_of_pad, pad_outer_lower_edge_y], 
                  [max_x + x_dist_pad_from_feedline + length_of_pad + thickness_of_pad, pad_outer_higher_edge_y], 
                  [max_x + x_dist_pad_from_feedline, pad_outer_higher_edge_y], 
                  [max_x, feedline_higher_max_y], 
                  [max_x, feedline_higher_min_y], 
                  [max_x + x_dist_pad_from_feedline, pad_inner_higher_edge_y], 
                  [max_x + x_dist_pad_from_feedline + length_of_pad, pad_inner_higher_edge_y], 
                  [max_x + x_dist_pad_from_feedline + length_of_pad, pad_inner_lower_edge_y], 
                  [max_x + x_dist_pad_from_feedline, pad_inner_lower_edge_y], 
                  [max_x, feedline_lower_max_y]]
        pad = gdspy.Polygon(points, layer=0)
        
        return pad
    
    if direction == "l":
        
        feedline_lower = feedline_left.polygons[0]
        feedline_higher = feedline_right.polygons[0]
        
        feedline_lower_min_y = np.min(feedline_lower[:, 1])
        feedline_lower_max_y = np.max(feedline_lower[:, 1])
        feedline_higher_min_y = np.min(feedline_higher[:, 1])
        feedline_higher_max_y = np.max(feedline_higher[:, 1])
        min_x = np.min(feedline_lower[:, 0])
        
        feedline_path_width = feedline_lower_max_y - feedline_lower_min_y
        feedline_width = feedline_higher_min_y - feedline_lower_max_y
        diff = thickness_of_pad - feedline_width
        feedline_gap_midpoint = np.mean([feedline_higher_min_y, feedline_lower_max_y])
        
        pad_inner_higher_edge_y = feedline_gap_midpoint + (width_of_pad / 2)
        pad_inner_lower_edge_y = feedline_gap_midpoint - (width_of_pad / 2)
        pad_outer_lower_edge_y = pad_inner_lower_edge_y - thickness_of_pad
        pad_outer_higher_edge_y = pad_inner_higher_edge_y + thickness_of_pad
                
        points = [[min_x, feedline_lower_max_y], 
                  [min_x, feedline_lower_min_y], 
                  [min_x - x_dist_pad_from_feedline, pad_outer_lower_edge_y], 
                  [min_x - x_dist_pad_from_feedline - length_of_pad - thickness_of_pad, pad_outer_lower_edge_y], 
                  [min_x - x_dist_pad_from_feedline - length_of_pad - thickness_of_pad, pad_outer_higher_edge_y], 
                  [min_x - x_dist_pad_from_feedline, pad_outer_higher_edge_y], 
                  [min_x, feedline_higher_max_y], 
                  [min_x, feedline_higher_min_y], 
                  [min_x - x_dist_pad_from_feedline, pad_inner_higher_edge_y], 
                  [min_x - x_dist_pad_from_feedline - length_of_pad, pad_inner_higher_edge_y], 
                  [min_x - x_dist_pad_from_feedline - length_of_pad, pad_inner_lower_edge_y], 
                  [min_x - x_dist_pad_from_feedline, pad_inner_lower_edge_y], 
                  [min_x, feedline_lower_max_y]]
        pad = gdspy.Polygon(points, layer=0)
        
        return pad
    
def create_holes(meander_config, hole_config):
    
    gap = meander_config.gap
    path_width = meander_config.path_width
    inner_angle = meander_config.inner_angle
    layers = meander_config.layers
    
    radius = hole_config.radius
    x_min = hole_config.x_min
    x_max = hole_config.x_max
    y_min = hole_config.y_min
    y_max = hole_config.y_max
    path1 = hole_config.path1
    path2 = hole_config.path2
    path3s = hole_config.path3s
    
    hole_period = int(0.5 * (gap + path_width) + inner_angle)

    hole_config.hole_periods.extend([hole_period])
    
    poly1 = [poly for poly in list(path1.polygons) if len(poly) == 4][1]
    poly2 = [poly for poly in list(path2.polygons) if len(poly) == 4][1]
    
    first_loop_y = np.mean([poly1[:, 1], poly2[:, 1]])
    
    holes = []
    
    y_min = int(first_loop_y - int(np.abs(y_min - first_loop_y) / hole_period) * hole_period)
    
    for x in range(x_min, x_max, hole_period):
        for y in range(y_min, y_max, hole_period):
            hole = gdspy.Round(center=(x, y), radius=radius, layer=layers[1])
            holes.append(hole)
        
    hole_objs = []
    
    for hole in holes:
        mergeds = []
        okay = True
        
        for path3 in path3s:
            mergeds.append(gdspy.boolean(hole, path3, "and"))
            
        for i in range(len(mergeds)):
            merged = mergeds[i]
            if merged is not None:
                okay = False
                
        if okay:
            hole_objs.append(hole)
            
    return hole_objs

def create_holes_no_meander(x_min, x_max, y_min, y_max, radius=5, hole_period=50, path3s=None, layers=[0, 1]):
    
    holes = []
    for x in range(x_min, x_max, hole_period):
        for y in range(y_min, y_max, hole_period):
            hole = gdspy.Round(center=(x, y), radius=radius, layer=layers[1])
            holes.append(hole)
        
    hole_objs = []
    
    for hole in holes:
        mergeds = []
        okay = True
        
        for path3 in path3s:
            mergeds.append(gdspy.boolean(hole, path3, "and"))
            
        for i in range(len(mergeds)):
            merged = mergeds[i]
            if merged is not None:
                okay = False
                
        if okay:
            hole_objs.append(hole)
            
    return hole_objs
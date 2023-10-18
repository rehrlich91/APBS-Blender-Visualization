import bpy
import pathlib
import csv
from math import radians
import glob
from mathutils import Vector

#########################################################################################

def purge_orphans():
    """
    Remove all orphan data blocks
    see this from more info:
    https://youtu.be/3rNqVPtbhzc?t=149
    """
    if bpy.app.version >= (3, 0, 0):
        # run this only for Blender versions 3.0 and higher
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    else:
        # run this only for Blender versions lower than 3.0
        # call purge_orphans() recursively until there are no more orphan data blocks to purge
        result = bpy.ops.outliner.orphans_purge()
        if result.pop() != "CANCELLED":
            purge_orphans()

#########################################################################################

def clearCollection():
    # New Collection
    my_coll = bpy.data.collections.new("Collection")
    # Add collection to scene collection
    bpy.context.scene.collection.children.link(my_coll)

    collect = bpy.data.collections['Collection']
    for ob in collect.objects:
        bpy.data.objects.remove(ob)
    return (collect)


#########################################################################################

def get_data(path):
    vertices, edges, faces = [], [], []
    r, g, b, hsv, energy = [], [], [], [], []
    # Read input file
    with open(path, 'r') as csvfile:
        datareader = csv.reader(csvfile)
        next(datareader)  # skip the first line
        for row in datareader:
            vertices.append((float(row[1]), float(row[2]), float(row[3])))  # Cartesian coordinates
            r.append(float(row[4]))  # RGB color inputs
            g.append(float(row[5]))
            b.append(float(row[6]))
            hsv.append(float(row[7]))  # HSV value
            energy.append(float(row[0]))  # APBS energy output
    return (r, g, b, hsv, energy, vertices, faces, edges)


#########################################################################################

def create_attributes(mesh, name, values):
    mesh.attributes.new(name=name, type="FLOAT", domain="POINT")
    mesh.attributes[name].data.foreach_set("value", values)

#########################################################################################

def rotate_object(object, axis, radian):
    object.rotation_euler[axis] += radians(radian)
    return (object)

#########################################################################################

def create_mesh(r, g, b, hsv, energy, vertices, faces, edges, gridName):
    new_mesh = bpy.data.meshes.new('apbsData')  # Instantiate new object
    new_mesh.from_pydata(vertices, edges, faces)  # Assign Cartesian coordinates to object
    new_mesh.update()

    # Create color and energy attributes
    create_attributes(new_mesh, 'r', r)
    create_attributes(new_mesh, 'g', g)
    create_attributes(new_mesh, 'b', b)
    create_attributes(new_mesh, 'hsv', hsv)
    create_attributes(new_mesh, 'energy', energy)

    obj = bpy.data.objects.new(gridName, new_mesh)  # Create grid object
    return (obj)

#########################################################################################

def active_object(obj):
    """
    returns the currently active object
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

#########################################################################################

def add_socket(ref):
    # access active object node_group
    node_group = bpy.context.object.modifiers[0].node_group
    inputs = node_group.inputs
    inputs.new(type="NodeSocketFloat", name=ref)

#########################################################################################

def add_socket_out(ref):
    # access active object node_group
    node_group = bpy.context.object.modifiers[0].node_group
    inputs = node_group.outputs
    inputs.new(type="NodeSocketColor", name=ref)

#########################################################################################

# def create_node(node_tree, type_name, node_x_location, node_location_step_x=0):
def create_node(node_tree, type_name, x_loc, y_loc):
    """Creates a node of a given type, and sets/updates the location of the node on the X axis.
    Returning the node object and the next location on the X axis for the next node.
    """

    node_obj = node_tree.nodes.new(type=type_name)
    node_obj.location.x = x_loc
    node_obj.location.y = y_loc

    return (node_obj)

#########################################################################################
def sample_gn_setup(geoNode_name):
    bpy.ops.node.new_geometry_nodes_modifier()
    bpy.data.node_groups["Geometry Nodes"].name = geoNode_name
    node_tree = bpy.data.node_groups[geoNode_name]

    # add socket to group input
    add_socket('energy')

#########################################################################################

def setup_gn(geoNode_name):
    bpy.ops.node.new_geometry_nodes_modifier()
    bpy.data.node_groups["Geometry Nodes"].name = geoNode_name
    node_tree = bpy.data.node_groups[geoNode_name]

    # add socket to group input
    add_socket('r')
    add_socket('g')
    add_socket('b')
    add_socket('hsv')
    add_socket('energy')
    add_socket_out('colors')

    # add GN to editor
    nodes = node_tree.nodes

    nodes["Group Input"].location.x = -10
    nodes["Group Output"].location.x = 900
    nodes["Group Output"].location.y = -50

    cube_mesh = create_node(node_tree, "GeometryNodeMeshCube", 125, -500)
    cube_mesh.inputs[0].default_value[0] = 1
    cube_mesh.inputs[0].default_value[1] = 1
    cube_mesh.inputs[0].default_value[2] = 1

    IOP_node = create_node(node_tree, "GeometryNodeInstanceOnPoints", 500, -100)
    RI_node = create_node(node_tree, "GeometryNodeRealizeInstances", 700, -50)
    combineColor_node = create_node(node_tree, "FunctionNodeCombineColor", 700, -150)
    setMaterial_node = create_node(node_tree, "GeometryNodeSetMaterial", 310, -375)

    absolute_math = create_node(node_tree, "ShaderNodeMath", 150, -100)
    absolute_math.operation = 'ABSOLUTE'

    greater_than = create_node(node_tree, "ShaderNodeMath", 310, -200)
    greater_than.operation = 'GREATER_THAN'

    add_math = create_node(node_tree, "ShaderNodeMath", 125, -300)
    add_math.operation = 'ADD'
    add_math.inputs[1].default_value = 0

    divide_math = create_node(node_tree, "ShaderNodeMath", -75, -250)
    divide_math.operation = 'DIVIDE'
    divide_math.inputs[1].default_value = 50

    scene_time = create_node(node_tree, "GeometryNodeInputSceneTime", -275, -250)
    bpy.context.scene.frame_end = 600

    # link GNs
    links = node_tree.links
    links.new(nodes["Group Input"].outputs["Geometry"], IOP_node.inputs['Points'])
    links.new(IOP_node.outputs["Instances"], RI_node.inputs["Geometry"])
    links.new(RI_node.outputs["Geometry"], nodes["Group Output"].inputs["Geometry"])
    links.new(cube_mesh.outputs["Mesh"], setMaterial_node.inputs["Geometry"])
    links.new(setMaterial_node.outputs["Geometry"], IOP_node.inputs["Instance"])
    links.new(nodes["Group Input"].outputs["r"], combineColor_node.inputs[0])
    links.new(nodes["Group Input"].outputs["g"], combineColor_node.inputs[1])
    links.new(nodes["Group Input"].outputs["b"], combineColor_node.inputs[2])
    links.new(nodes["Group Input"].outputs["hsv"], combineColor_node.inputs[3])
    links.new(nodes["Group Input"].outputs["energy"], absolute_math.inputs["Value"])
    links.new(absolute_math.outputs["Value"], greater_than.inputs['Value'])
    links.new(greater_than.outputs['Value'], IOP_node.inputs['Selection'])
    links.new(combineColor_node.outputs["Color"], nodes["Group Output"].inputs["colors"])
    links.new(scene_time.outputs['Frame'], divide_math.inputs[0])
    links.new(divide_math.outputs['Value'], add_math.inputs[0])
    links.new(add_math.outputs['Value'], greater_than.inputs[1])

    bpy.context.object.modifiers['GeometryNodes']['Input_2_attribute_name'] = "r"
    bpy.context.object.modifiers['GeometryNodes']['Input_3_attribute_name'] = "g"
    bpy.context.object.modifiers['GeometryNodes']['Input_4_attribute_name'] = "b"
    bpy.context.object.modifiers['GeometryNodes']['Input_5_attribute_name'] = "hsv"
    bpy.context.object.modifiers['GeometryNodes']['Input_6_attribute_name'] = "energy"
    bpy.context.object.modifiers["GeometryNodes"]["Output_7_attribute_name"] = "colorOut"

    bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_2_use_attribute\"]",
                                                         modifier_name="GeometryNodes")
    bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_3_use_attribute\"]",
                                                         modifier_name="GeometryNodes")
    bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_4_use_attribute\"]",
                                                         modifier_name="GeometryNodes")
    bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_5_use_attribute\"]",
                                                         modifier_name="GeometryNodes")
    bpy.ops.object.geometry_nodes_input_attribute_toggle(prop_path="[\"Input_6_use_attribute\"]",
                                                         modifier_name="GeometryNodes")


#########################################################################################
def setup_sn(geoNode_name, shaderName):
    # Create a new material
    material = bpy.data.materials.new(name=shaderName)
    material.use_nodes = True

    mat_nodes = material.node_tree

    # Get the node in its node tree (replace the name below)
    drop_node = mat_nodes.nodes['Principled BSDF']
    mat_nodes.nodes.remove(drop_node)
    # test = material.node_tree.nodes.get('Principled BSDF')
    # subsurf_node = material.node_tree.nodes.new(type='ShaderNodeSubsurfaceScattering')
    # attribute_node = material.node_tree.nodes.new(type='ShaderNodeAttribute')

    subsurf_node = create_node(mat_nodes, "ShaderNodeSubsurfaceScattering", 0, 0)
    attribute_node = create_node(mat_nodes, "ShaderNodeAttribute", -250, 0)

    mat_nodes.nodes["Material Output"].location.x = 250
    mat_nodes.nodes["Material Output"].location.y = 0

    bpy.data.materials[shaderName].node_tree.nodes["Attribute"].attribute_name = "colorOut"

    links = mat_nodes.links
    links.new(attribute_node.outputs['Color'], subsurf_node.inputs['Color'])
    links.new(subsurf_node.outputs['BSSRDF'], mat_nodes.nodes["Material Output"].inputs['Surface'])

    bpy.data.node_groups[geoNode_name].nodes["Set Material"].inputs[2].default_value = bpy.data.materials[shaderName]


#########################################################################################
# Main Program                                                                          #
#########################################################################################

if __name__ == '__main__':
    collect = bpy.data.collections.get('Collection')
    path = "%s/*.csv" % (''.join(glob.glob('path to input file')))  # path to input file folder

    input_files = sorted(glob.glob(path))

    for i in range(len(input_files)):
        file = input_files[i]
        r, g, b, hsv, energy, vertices, faces, edges = get_data(file)
        start, end = file.rfind('/'), file.rfind('_')
        gridName = file[start + 1:]
        object = create_mesh(r, g, b, hsv, energy, vertices, faces, edges, gridName)
        rot_obj = rotate_object(object, 0, -90)
        rot_obj.location.x += (i * 75)
        collect.objects.link(rot_obj)
        active_object(rot_obj)
        geoNode_name = 'geometry_node_grid_%s' % (i)
        shaderNode_name = 'shader_node_grid_%s' % (i)
        setup_gn(geoNode_name)
        setup_sn(geoNode_name, shaderNode_name)

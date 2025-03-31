import math
import ezdxf
import operator
import functools
from ezdxf import edgesmith, edgeminer

doc = ezdxf.readfile("test3.dxf")
modelspace = doc.modelspace()

# get all entities in the document
entities = modelspace.entity_space
print(f"Entities found: {[str(entity) for entity in entities]}")

# courtesy of gemini
# counterclockwise from v1 to v2
def counterclockwise_angle_degrees(v1, v2):
    a, b = v1
    c, d = v2
    dot_product = a * c + b * d
    magnitude_v1 = math.sqrt(a**2 + b**2)
    magnitude_v2 = math.sqrt(c**2 + d**2)
    if magnitude_v1 == 0 or magnitude_v2 == 0:
        return 0.0
    cosine_angle = dot_product / (magnitude_v1 * magnitude_v2)
    angle_radians = math.acos(max(min(cosine_angle, 1.0), -1.0)) # Ensure angle is within valid range
    cross_product = a * d - b * c
    if cross_product < 0:
        angle_degrees = math.degrees(angle_radians)
    else:
        angle_degrees = 360 - math.degrees(angle_radians)
    return angle_degrees

# process circles/flattened into arcs
to_delete = []
print("processing circles")
for entity in entities:
    if "CIRCLE" in str(entity):
        print(f"found circle {str(entity)}")
        to_delete.append(entity)
        flattened = list(entity.flattening(entity.dxf.radius / 3.0))
        print(f"handling {len(flattened)} points")
        circlecenter = entity.dxf.center
        for index, _ in enumerate(flattened):
            # points are returned CCW order
            p1 = flattened[index]
            p2 = flattened[(index + 1) % len(flattened)]
            v1 = [circlecenter[0] - p1[0], circlecenter[1] - p1[1]]
            v2 = [circlecenter[0] - p2[0], circlecenter[1] - p2[1]]
            v_east = [1, 0]
            a1 = counterclockwise_angle_degrees(v_east, v1)
            a2 = counterclockwise_angle_degrees(v_east, v2)
            modelspace.add_arc(center=entity.dxf.center, radius=entity.dxf.radius, start_angle=a1, end_angle=a2)
print("done processing circles")

# get all edges (i.e. non-circles (?))
edges = list(edgesmith.edges_from_entities_2d(entities))
print(f"Edges found: {edges}")

# find all closed loops
deposit = edgeminer.Deposit(edges)
loops = edgeminer.find_all_loops(deposit)
print(f"Loops found: {loops}")

# so we know what to not add when recreating the dxf
items_to_ignore = set()
outloops = []
for l in loops:
    outloops.extend(l)
for edge in list(outloops):
    items_to_ignore.add(str(edge.payload))
print(f"{len(items_to_ignore)} edges now unnecessary: {items_to_ignore}")

# create the polylines
# new_polylines = [edgesmith.polyline_path_from_chain(loop) for loop in loops]
# new_polylines = [edgesmith.polyline2d_from_chain(loop) for loop in loops]
new_polylines = [edgesmith.lwpolyline_from_chain(loop) for loop in loops]
print(f"Polylines created: {[str(line) for line in new_polylines]}")
# for polyline in new_polylines:
#     print(polyline.get_points())


# edit the dxf
for entity in entities:
    if str(entity) in items_to_ignore:
        to_delete.append(entity)
for item in to_delete:
    modelspace.delete_entity(item)

for polyline in new_polylines:
    # force the polyline to be closed
    polyline.close()

    # add polyline to modelspace
    # modelspace.add_polyline2d(polyline.points(), close=True)
    modelspace.add_lwpolyline(polyline.get_points())

print(f"Entities in entity space: {[*modelspace.entity_space]}")

doc.saveas("out.dxf")
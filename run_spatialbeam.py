from __future__ import division
import numpy
import sys
import time

from openmdao.api import IndepVarComp, Problem, Group, ScipyOptimizer, SqliteRecorder, setup_profiling, activate_profiling
from geometry import GeometryMesh, mesh_gen, LinearInterp
from spatialbeam import SpatialBeamStates, SpatialBeamFunctionals, radii
from materials import MaterialsTube
from openmdao.devtools.partition_tree_n2 import view_tree

# Create the mesh with 2 inboard points and 3 outboard points
mesh = mesh_gen(n_points_inboard=4, n_points_outboard=6)
# mesh = mesh_gen(n_points_inboard=2, n_points_outboard=2)

num_y = mesh.shape[1]
r = radii(mesh)
t = r/10

# Define the material properties
execfile('aluminum.py')

# Define the loads
loads = numpy.zeros((num_y, 6))
loads[0, 2] = loads[-1, 2] = 1e3 # tip load of 1 kN
loads[:, 2] = 1e3 # load of 1 kN at each node

span = 58.7630524 # [m] baseline CRM

root = Group()

des_vars = [
    ('twist', numpy.zeros(num_y)),
    ('span', span),
    ('r', r),
    ('t', t),
    ('loads', loads)
]

root.add('des_vars',
         IndepVarComp(des_vars),
         promotes=['*'])
root.add('mesh',
         GeometryMesh(mesh),
         promotes=['*'])
root.add('tube',
         MaterialsTube(num_y),
         promotes=['*'])
root.add('spatialbeamstates',
         SpatialBeamStates(num_y, E, G),
         promotes=['*'])
root.add('spatialbeamfuncs',
         SpatialBeamFunctionals(num_y, E, G, stress, mrho),
         promotes=['*'])

prob = Problem()
prob.root = root

prob.driver = ScipyOptimizer()
prob.driver.options['optimizer'] = 'SLSQP'
prob.driver.options['disp'] = True
# prob.driver.options['tol'] = 1.0e-12

prob.driver.add_desvar('t',
                       lower=numpy.ones((num_y)) * 0.003,
                       upper=numpy.ones((num_y)) * 0.25)
prob.driver.add_objective('energy')
prob.driver.add_constraint('weight', upper=1e5)

prob.root.deriv_options['type'] = 'cs'

prob.driver.add_recorder(SqliteRecorder('spatialbeam.db'))

setup_profiling(prob)
activate_profiling()

prob.setup()
view_tree(prob, outfile="spatialbeam.html", show_browser=False)

if sys.argv[1] == '0':
    prob.check_partial_derivatives(compact_print=True)
    # prob.check_total_derivatives()
    prob.run_once()
    print
    print prob['A']
    print prob['Iy']
    print prob['Iz']
    print prob['J']
    print
    print prob['disp']
elif sys.argv[1] == '1':

    st = time.time()
    prob.run()
    print "weight", prob['weight']
    print "run time", time.time()-st

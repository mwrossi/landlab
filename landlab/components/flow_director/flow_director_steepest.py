#! /usr/env/python

"""
flow_director_steepest.py: provides the component FlowDirectorSteepest.

This components finds the steepest single-path steepest descent flow
directions. It is equivalent to D4 method in the special case of a raster grid
in that it does not consider diagonal links between nodes. For that capability,
use FlowDirectorD8.
"""

from landlab.components.flow_director.flow_director_to_one import _FlowDirectorToOne
from landlab.components.flow_director import flow_direction_DN
from landlab import VoronoiDelaunayGrid
from landlab import BAD_INDEX_VALUE, FIXED_VALUE_BOUNDARY, FIXED_GRADIENT_BOUNDARY
import numpy


class FlowDirectorSteepest(_FlowDirectorToOne):

    """Single-path (steepest direction) flow direction without diagonals.

    This components finds the steepest single-path steepest descent flow
    directions. It is equivalent to D4 method in the special case of a raster
    grid in that it does not consider diagonal links between nodes. For that
    capability, use FlowDirectorD8.

    Stores as ModelGrid fields:

    -  Node array of receivers (nodes that receive flow), or ITS OWN ID if
       there is no receiver: *'flow__receiver_node'*
    -  Node array of steepest downhill slopes:
       *'topographic__steepest_slope'*
    -  Node array containing ID of link that leads from each node to its
       receiver, or BAD_INDEX_VALUE if no link:
       *'flow__link_to_receiver_node'*
    -  Boolean node array of all local lows: *'flow__sink_flag'*
    -  Link array identifing if flow goes with (1) or against (-1) the link
       direction: *'flow__link_direction'*

    The primary method of this class is :func:`run_one_step`.

    Examples
    --------

    This method works for both raster and irregular grids. First we will look
    at a raster example, and then an irregular example.

    >>> import numpy as np
    >>> from landlab import RasterModelGrid
    >>> from landlab.components import FlowDirectorSteepest
    >>> mg = RasterModelGrid((3,3), spacing=(1, 1))
    >>> mg.set_closed_boundaries_at_grid_edges(True, True, True, False)
    >>> _ = mg.add_field('topographic__elevation',
    ...                  mg.node_x + mg.node_y,
    ...                  at = 'node')
    >>> fd = FlowDirectorSteepest(mg, 'topographic__elevation')
    >>> fd.surface_values
    array([ 0.,  1.,  2.,  1.,  2.,  3.,  2.,  3.,  4.])
    >>> fd.run_one_step()
    >>> mg.at_node['flow__receiver_node']
    array([0, 1, 2, 3, 1, 5, 6, 7, 8])
    >>> mg.at_node['topographic__steepest_slope']
    array([ 0.,  0.,  0.,  0.,  1.,  0.,  0.,  0.,  0.])
    >>> mg.at_node['flow__link_to_receiver_node']
    array([-1, -1, -1, -1,  3, -1, -1, -1, -1])
    >>> mg.at_node['flow__sink_flag']
    array([1, 1, 1, 1, 0, 1, 1, 1, 1], dtype=int8)
    >>> mg_2 = RasterModelGrid((5, 4), spacing=(1, 1))
    >>> topographic__elevation = np.array([0.,  0.,  0., 0.,
    ...                                    0., 21., 10., 0.,
    ...                                    0., 31., 20., 0.,
    ...                                    0., 32., 30., 0.,
    ...                                    0.,  0.,  0., 0.])
    >>> _ = mg_2.add_field('node',
    ...                    'topographic__elevation',
    ...                    topographic__elevation)
    >>> mg_2.set_closed_boundaries_at_grid_edges(True, True, True, False)
    >>> fd_2 = FlowDirectorSteepest(mg_2)
    >>> fd_2.run_one_step()
    >>> mg_2.at_node['flow__receiver_node'] # doctest: +NORMALIZE_WHITESPACE
    array([ 0,  1,  2,  3,
            4,  1,  2,  7,
            8, 10,  6, 11,
           12, 14, 10, 15,
           16, 17, 18, 19])

    And the at-link field ``'flow__link_direction'`` indicates if the flow along
    the link is with or against the direction indicated by ``'link_dirs_at_node'``
    (from tail node to head node).

    >>> mg_2.at_link['flow__link_direction']
    array([ 0,  0,  0,  0, -1, -1,  0,  0,  0,  0,  0,  0, -1,  0,  0,  1,  0,
        0,  0, -1,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0])

    This indicates that flow on links 4, 5, 12, and 19 goes against the
    topologic ordering -- that is that flow goes from head node to tail node --
    and that flow goes with the topologic ordering on links 15 and 22. All other
    links have no flow on them.

    The FlowDirectorSteepest attribute ``flow__link_direction_at_node`` indicates
    the link flow direction (with or against topology directions) for all links
    at node. The ordering of links at node mirrors the grid attribute
    ``links_at_node``.

    >>> fd_2.flow__link_direction_at_node
    array([[ 0,  0,  0,  0],
           [ 0, -1,  0,  0],
           [ 0, -1,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0, -1],
           [ 0, -1,  0, -1],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 1,  0,  0,  0],
           [ 0, -1,  1, -1],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 1,  0,  0,  0],
           [ 0,  0,  1, -1],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0]])

    For example, this indicates that node 10 has flow going along three links
    that are attached to it. The link to the East has no flow, the link to the
    North has flow going against the topologic direction, the link to the West
    has flow going with the topologic direction, and the link to the South has
    flow going against the topologic direction.

    In many use cases, one might want to know which links are bringing flow into
    or out of the node. The flow director attribute ``flow__link_incoming_at_node``
    provides this information. Here -1 means that flow is outgoing from the node
    and 1 means it is incoming.

    >>> fd_2.flow__link_incoming_at_node
    array([[ 0,  0,  0,  0],
           [ 0,  1,  0,  0],
           [ 0,  1,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0, -1],
           [ 0,  1,  0, -1],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [-1,  0,  0,  0],
           [ 0,  1,  1, -1],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [-1,  0,  0,  0],
           [ 0,  0,  1, -1],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0],
           [ 0,  0,  0,  0]])

    So if one wanted to identify the source nodes at node, you would do the
    following:

    >>> np.where(fd_2.flow__link_incoming_at_node == 1, mg_2.adjacent_nodes_at_node, -1)
    array([[-1, -1, -1, -1],
           [-1,  5, -1, -1],
           [-1,  6, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, 10, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, 14,  9, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, 13, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1],
           [-1, -1, -1, -1]])

    The flow directors also have the ability to return the flow receiver nodes

    >>> receiver = fd.direct_flow()
    >>> receiver
    array([0, 1, 2,
           3, 1, 5,
           6, 7, 8])

    For the second example we will use a Hexagonal Model Grid, a special type
    of Voroni Grid that has regularly spaced hexagonal cells.

    >>> from landlab import HexModelGrid
    >>> mg = HexModelGrid(5,3)
    >>> _ = mg.add_field('topographic__elevation',
    ...                  mg.node_x + np.round(mg.node_y),
    ...                  at = 'node')
    >>> fd = FlowDirectorSteepest(mg, 'topographic__elevation')
    >>> fd.surface_values
    array([ 0. ,  1. ,  2. ,
        0.5,  1.5,  2.5,  3.5,
      1. ,  2. ,  3. ,  4. , 5. ,
        2.5,  3.5,  4.5,  5.5,
            3. ,  4. ,  5. ])
    >>> fd.run_one_step()
    >>> mg.at_node['flow__receiver_node']
    array([ 0,  1,  2,
          3,  0,  1,  6,
        7,  3,  4,  5,  11,
          12,  8,  9, 15,
            16, 17, 18])
    >>> mg.at_node['topographic__steepest_slope']
    array([ 0. ,  0. ,  0. ,
        0. ,  1.5,  1.5,   0. ,
      0. ,  1.5,  1.5,  1.5,  0. ,
        0. ,  1.5,  1.5,  0. ,
            0. ,  0. ,  0. ])
    >>> mg.at_node['flow__link_to_receiver_node']
    array([-1, -1, -1,
         -1,  3,  5, -1,
       -1, 12, 14, 16, -1,
         -1, 25, 27, -1,
           -1, -1, -1])
    >>> mg.at_node['flow__sink_flag']
    array([1, 1, 1,
          1, 0, 0, 1,
         1, 0, 0, 0, 1,
          1, 0, 0, 1,
            1, 1, 1], dtype=int8)
    >>> receiver = fd.direct_flow()
    >>> receiver
    array([ 0,  1,  2,
          3,  0,  1,  6,
        7,  3,  4,  5, 11,
         12,  8,  9, 15,
          16, 17, 18])
    """

    _name = "FlowDirectorSteepest"

    def __init__(self, grid, surface="topographic__elevation"):
        """
        Parameters
        ----------
        grid : ModelGrid
            A grid.
        surface : field name at node or array of length node, optional
            The surface to direct flow across, default is field at node:
            topographic__elevation,.
        """
        self.method = "D4"
        super(FlowDirectorSteepest, self).__init__(grid, surface)
        self._is_Voroni = isinstance(self._grid, VoronoiDelaunayGrid)

        # create a : 'flow__link_direction' field if it does not exist yest
        if "flow__link_direction" not in self._grid.at_link:
            self._flow__link_direction = grid.add_field(
                "flow__link_direction",
                grid.zeros(at="link", dtype=int),
                at="link",
                dtype=int,
            )
        else:
            self._flow__link_direction = grid.at_link["flow__link_direction"]

        self.updated_boundary_conditions()

    def updated_boundary_conditions(self):
        """
        Method to update FlowDirectorSteepest when boundary conditions change.

        Call this if boundary conditions on the grid are updated after the
        component is instantiated.
        """
        self._active_links = self.grid.active_links
        self._activelink_tail = self.grid.node_at_link_tail[self.grid.active_links]
        self._activelink_head = self.grid.node_at_link_head[self.grid.active_links]

    def run_one_step(self):
        """
        Find flow directions and save to the model grid.

        run_one_step() checks for updated boundary conditions, calculates
        slopes on links, finds baselevel nodes based on the status at node,
        calculates flow directions, and saves results to the grid.

        An alternative to direct_flow() is run_one_step() which does the same
        things but also returns the receiver nodes not return values.
        """
        self.direct_flow()

    def direct_flow(self):
        """
        Find flow directions, save to the model grid, and return receivers.

        direct_flow() checks for updated boundary conditions, calculates
        slopes on links, finds baselevel nodes based on the status at node,
        calculates flow directions, saves results to the grid, and returns a
        at-node array  of receiver nodes. This array is stored in the grid at:
        grid['node']['flow__receiver_node']

        An alternative to direct_flow() is run_one_step() which does the same
        things but also returns a at-node array  of receiver nodes. This array
        is stored in the grid at:
        grid['node']['flow__receiver_node']
        """
        self._check_updated_bc()

        # update the surface, if it was provided as a model grid field.
        self._changed_surface()

        # step 1. Calculate link slopes at active links only.
        all_grads = -self._grid.calc_grad_at_link(self.surface_values)
        link_slope = all_grads[self._grid.active_links]

        # Step 2. Find and save base level nodes.
        (baselevel_nodes,) = numpy.where(
            numpy.logical_or(
                self._grid.status_at_node == FIXED_VALUE_BOUNDARY,
                self._grid.status_at_node == FIXED_GRADIENT_BOUNDARY,
            )
        )

        # Calculate flow directions
        receiver, steepest_slope, sink, recvr_link = flow_direction_DN.flow_directions(
            self.surface_values,
            self._active_links,
            self._activelink_tail,
            self._activelink_head,
            link_slope,
            grid=self._grid,
            baselevel_nodes=baselevel_nodes,
        )

        # Save the four ouputs of this component.
        self._grid["node"]["flow__receiver_node"][:] = receiver
        self._grid["node"]["topographic__steepest_slope"][:] = steepest_slope
        self._grid["node"]["flow__link_to_receiver_node"][:] = recvr_link
        self._grid["node"]["flow__sink_flag"][:] = numpy.zeros_like(
            receiver, dtype=bool
        )
        self._grid["node"]["flow__sink_flag"][sink] = True

        # determine link directions
        self._determine_link_directions()

        return receiver

    def _determine_link_directions(self):
        """Determine link directions and set flow__link_direction field.

        This routine is slightly different between the route-to-one and
        route-to-many methods.

        An additional issue may be if this also needs to be updated by
        depression finding.
        """
        # start by re-setting all links to zero.
        self._flow__link_direction[:] = 0

        # grid.link_dirs_at_node: 0 = NA, -1 = out of (this node is HEAD)
        # -1 = into (this node is TAIL)

        # grid.links_at_node = Link ID at node

        # grid.node_at_link_head = node ID at link HEAD
        # grid.node_at_link_tail = node ID at link tail

        # links that are used are in `flow__link_to_receiver_node`.
        # if `flow__link_to_receiver_node` is leading to the link HEAD node,
        # then -1, otherwise 1 (double check this is not the reverse).

        # identify where flow is active on links
        is_active_flow_link = self.links_to_receiver != BAD_INDEX_VALUE

        # make an array that says which link ID is active
        active_flow_links = self.links_to_receiver[is_active_flow_link]

        # for each of those links, the position is the upstream node
        upstream_node_of_active_flow_link = numpy.where(is_active_flow_link)[0]

        # get the head node
        head_node_at_active_flow_link = self._grid.node_at_link_head[active_flow_links]

        # if head node is upstream node = -1, else 1
        self._flow__link_direction[
            active_flow_links[
                head_node_at_active_flow_link == upstream_node_of_active_flow_link
            ]
        ] = -1
        self._flow__link_direction[
            active_flow_links[
                head_node_at_active_flow_link != upstream_node_of_active_flow_link
            ]
        ] = 1

    @property
    def flow__link_direction_at_node(self):
        """Return array that mirrors links at node that indicates flow direction."""
        flow__link_direction_at_node = self.flow__link_direction[
            self._grid.links_at_node
        ]
        flow__link_direction_at_node[self._grid.links_at_node == -1] = 0
        return flow__link_direction_at_node

    @property
    def flow__link_incoming_at_node(self):
        """Return array that mirrors links at node and indicates if flow is
        incoming (1) or outgoing (-1)."""
        incoming_at_node = (
            self.flow__link_direction_at_node * self._grid.link_dirs_at_node
        )
        return incoming_at_node

    # Number of Link (or number of D8)
    @property
    def flow__link_direction(self):
        """Return the array indicating if flow is going with or against link direction."""
        return self._flow__link_direction

    @property
    def upstream_node_at_link(self):
        """At-link array of the upstream node"""
        out = -1 * self._grid.ones(at="link", dtype=int)
        out[self._flow__link_direction == 1] = self._grid.node_at_link_tail[
            self._flow__link_direction == 1
        ]
        out[self._flow__link_direction == -1] = self._grid.node_at_link_head[
            self._flow__link_direction == -1
        ]
        return out

    @property
    def downstream_node_at_link(self):
        """At-link array of the downstream node"""
        out = -1 * self._grid.ones(at="link", dtype=int)
        out[self._flow__link_direction == 1] = self._grid.node_at_link_head[
            self._flow__link_direction == 1
        ]
        out[self._flow__link_direction == -1] = self._grid.node_at_link_tail[
            self._flow__link_direction == -1
        ]
        return out


if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod()

"""This module defines miscellaneous utility functions."""

import numpy as np

from numpy import unique, linalg, diag, sqrt, dot
import scipy.cluster.hierarchy as sch
from scipy import spatial
from .misctools import addBreaks, interpY
from Bio import Phylo

__all__ = ['calcTree', 'clusterMatrix', 'showLines', 'showMatrix', 'reorderMatrix', 'findSubgroups']

def calcTree(names, distance_matrix, method='nj'):
    """ Given a distance matrix for an ensemble, it creates an returns a tree structure.
    :arg names: an list of names. 
    :type names: list-like
    :arg distance_matrix: a square matrix with length of ensemble. If numbers does not mismatch
    it will raise an error. 
    :type distance_matrix: numpy.ndarray 
    """
    try: 
        from Bio import Phylo
    except ImportError:
        raise ImportError('Phylo module could not be imported. '
            'Reinstall ProDy or install Biopython '
            'to solve the problem.')
    
    if len(names) != distance_matrix.shape[0] or len(names) != distance_matrix.shape[1]:
        raise ValueError("Mismatch between the sizes of matrix and names.")

    matrix = []
    k = 1
    for row in distance_matrix:
        matrix.append(list(row[:k]))
        k = k + 1
    from Bio.Phylo.TreeConstruction import _DistanceMatrix
    dm = _DistanceMatrix(names, matrix)
    constructor = Phylo.TreeConstruction.DistanceTreeConstructor()

    method = method.strip().lower()
    if method == 'nj':
        tree = constructor.nj(dm)
    elif method == 'upgma':
        tree = constructor.upgma(dm)
    else:
        raise ValueError('Method can be only either "nj" or "upgma".')

    for node in tree.get_nonterminals():
        node.name = None
    return tree

def clusterMatrix(distance_matrix=None, similarity_matrix=None, labels=None, return_linkage=None, **kwargs):
    """
    Cluster a distance matrix using scipy.cluster.hierarchy and 
    return the sorted matrix, indices used for sorting, sorted labels (if **labels** are passed),  
    and linkage matrix (if **return_linkage** is **True**). Set ``similarity=True`` for clustering a similarity matrix
    
    :arg distance_matrix: an N-by-N matrix containing some measure of distance 
        such as 1. - seqid_matrix, rmsds, or distances in PCA space
    :type similarity_matrix: :class:`~numpy.ndarray`

    :arg similarity_matrix: an N-by-N matrix containing some measure of similarity 
        such as sequence identity, mode-mode overlap, or spectral overlap
    :type similarity_matrix: :class:`~numpy.ndarray`
    
    :arg labels: labels for each matrix row that can be returned sorted
    :type labels: list

    :arg no_plot: if **True**, don't plot the dendrogram.
        default is **True**
    :type no_plot: bool
    
    :arg reversed: if set to **True**, then the sorting indices will be reversed.
    :type reversed: bool

    Other arguments for :method:`~scipy.hierarchy.linkage` and :method:`~scipy.hierarchy.dendrogram`
        can also be provided and will be taken as **kwargs**.
    """

    if similarity_matrix is None and distance_matrix is None:
        raise ValueError('Please provide a distance matrix or a similarity matrix')
    
    orientation = kwargs.pop('orientiation', 'right')
    reversed = kwargs.pop('reversed', False)
    no_plot = kwargs.pop('no_plot', True)

    if distance_matrix is None:
        matrix = similarity_matrix
        distance_matrix = 1. - similarity_matrix
    else:
        matrix = distance_matrix
        
    formatted_distance_matrix = spatial.distance.squareform(distance_matrix)
    linkage_matrix = sch.linkage(formatted_distance_matrix, **kwargs)
    sorting_dendrogram = sch.dendrogram(linkage_matrix, orientation=orientation, labels=labels, no_plot=no_plot)

    indices = sorting_dendrogram['leaves']
    sorted_labels = sorting_dendrogram['ivl']

    if reversed:
        indices = indices[::-1]
        sorted_labels = sorted_labels[::-1]
    
    sorted_matrix = matrix[indices, :]
    sorted_matrix = sorted_matrix[:, indices]
    
    return_vals = [sorted_matrix, indices]

    if labels is not None:
        return_vals.append(sorted_labels)
    if return_linkage:
        return_vals.append(linkage_matrix)
    return tuple(return_vals) # convert to tuple to avoid [pylint] E0632:Possible unbalanced tuple unpacking

def showLines(*args, **kwargs):
    """
    Show 1-D data using :func:`~matplotlib.axes.Axes.plot`. 
    
    :arg x: (optional) x coordinates. *x* can be an 1-D array or a 2-D matrix of 
    column vectors.
    :type x: `~numpy.ndarray`

    :arg y: data array. *y* can be an 1-D array or a 2-D matrix of 
    column vectors.
    :type y: `~numpy.ndarray`

    :arg dy: an array of variances of *y* which will be plotted as a 
    band along *y*. It should have the same shape with *y*.
    :type dy: `~numpy.ndarray`

    :arg alpha: the transparency of the band(s).
    :type alpha: float

    :arg ticklabels: user-defined tick labels for x-axis.
    :type ticklabels: list
    """
    
    # note for developers: this function serves as a low-level 
    # plotting function which provides basic utilities for other 
    # plotting functions. Therefore showFigure is not handled 
    # in this function as it should be already handled in the caller.

    ticklabels = kwargs.pop('ticklabels', None)
    dy = kwargs.pop('dy', None)
    alpha = kwargs.pop('alpha', 0.5)
    gap = kwargs.pop('gap', False)

    from matplotlib import cm, ticker
    from matplotlib.pyplot import figure, gca, xlim

    ax = gca()
    lines = ax.plot(*args, **kwargs)

    polys = []
    if dy is not None:
        dy = np.array(dy)
        if dy.ndim == 1:
            n, = dy.shape; m = 1
        elif dy.ndim == 2:
            n, m = dy.shape
        else:
            raise ValueError('dy should be either 1-D or 2-D.')
        
        for i, line in enumerate(lines):
            color = line.get_color()
            x, y = line.get_data()
            if m != 1 and m != len(lines) or n != len(y):
                raise ValueError('The shapes of dy and y do not match.')

            if dy.ndim == 1:
                _dy = dy
            else:
                _dy = dy[:, i]
            
            if gap:
                x_new, y_new = addBreaks(x, y)
                line.set_data(x_new, y_new)
                _, _dy = addBreaks(x, _dy)
            else:
                x_new, y_new = x, y

            poly = ax.fill_between(x_new, y_new-_dy, y_new+_dy,
                                   alpha=alpha, facecolor=color, edgecolor=None,
                                   linewidth=1, antialiased=True)
            polys.append(poly)

    ax.margins(x=0)
    if ticklabels is not None:
        ax.get_xaxis().set_major_formatter(ticker.IndexFormatter(ticklabels))
    
    ax.xaxis.set_major_locator(ticker.AutoLocator())
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())

    return lines, polys

def showMatrix(matrix, x_array=None, y_array=None, **kwargs):
    """Show a matrix using :meth:`~matplotlib.axes.Axes.imshow`. Curves on x- and y-axis can be added.
    :arg matrix: Matrix to be displayed.
    :type matrix: :class:`~numpy.ndarray`
    :arg x_array: Data to be plotted above the matrix.
    :type x_array: :class:`~numpy.ndarray`
    :arg y_array: Data to be plotted on the left side of the matrix.
    :type y_array: :class:`~numpy.ndarray`
    :arg percentile: A percentile threshold to remove outliers, i.e. only showing data within *p*-th 
                     to *100-p*-th percentile.
    :type percentile: float"""

    import matplotlib.pyplot as plt
    from matplotlib import cm, ticker
    from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
    from matplotlib.collections import LineCollection
    from matplotlib.pyplot import imshow, gca, sca, sci

    p = kwargs.pop('percentile', None)
    if p is not None:
        vmin = np.percentile(matrix, p)
        vmax = np.percentile(matrix, 100-p)
    else:
        vmin = vmax = None
    
    W = H = kwargs.pop('ratio', 6)

    ticklabels = kwargs.pop('ticklabels', None)
    allticks = kwargs.pop('allticks', False) # this argument is temporary and will be replaced by better implementation
    origin = kwargs.pop('origin', 'lower')

    if x_array is not None and y_array is not None:
        nrow = 2; ncol = 2
        i = 1; j = 1
        width_ratios = [1, W]
        height_ratios = [1, H]
        aspect = 'auto'
    elif x_array is not None and y_array is None:
        nrow = 2; ncol = 1
        i = 1; j = 0
        width_ratios = [W]
        height_ratios = [1, H]
        aspect = 'auto'
    elif isinstance(y_array, Phylo.BaseTree.Tree):
        nrow = 2; ncol = 2
        i = 1; j = 1
        width_ratios = [W, W]
        height_ratios = [H, H]
        aspect = 'auto'
    elif x_array is None and y_array is not None:
        nrow = 1; ncol = 2
        i = 0; j = 1
        width_ratios = [1, W]
        height_ratios = [H]
        aspect = 'auto'
    else:
        nrow = 1; ncol = 1
        i = 0; j = 0
        width_ratios = [W]
        height_ratios = [H]
        aspect = None

    main_index = (i,j)
    upper_index = (i-1,j)
    left_index = (i,j-1)

    complex_layout = nrow > 1 or ncol > 1
    cb = kwargs.pop('colorbar', True)

    ax1 = ax2 = ax3 = None

    if complex_layout:
        gs = GridSpec(nrow, ncol, width_ratios=width_ratios, 
                      height_ratios=height_ratios, hspace=0., wspace=0.)

    lines = []
    if nrow > 1:
        ax1 = plt.subplot(gs[upper_index])

        if isinstance(y_array, Phylo.BaseTree.Tree):
            pass

        else:
            ax1.set_xticklabels([])
            
            y = x_array
            xp, yp = interpY(y)
            points = np.array([xp, yp]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            lcy = LineCollection(segments, array=yp, linewidths=1, cmap='jet')
            lines.append(lcy)
            ax1.add_collection(lcy)

            ax1.set_xlim(xp.min(), xp.max())
            ax1.set_ylim(yp.min(), yp.max())
        ax1.axis('off')

    if ncol > 1:
        ax2 = plt.subplot(gs[left_index])
        
        if isinstance(y_array, Phylo.BaseTree.Tree):
            Phylo.draw(y_array, do_show=False, axes=ax2, **kwargs)
        else:
            ax2.set_xticklabels([])
            
            y = y_array
            xp, yp = interpY(y)
            points = np.array([yp, xp]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            lcx = LineCollection(segments, array=yp, linewidths=1, cmap='jet')
            lines.append(lcx)
            ax2.add_collection(lcx)
            ax2.set_xlim(yp.min(), yp.max())
            ax2.set_ylim(xp.min(), xp.max())
            ax2.invert_xaxis()

        ax2.axis('off')

    if complex_layout:
        ax3 = plt.subplot(gs[main_index])
    else:
        ax3 = gca()
    
    kwargs['origin'] = origin
    if not 'cmap' in kwargs:
        kwargs['cmap'] = 'jet'
    im = ax3.imshow(matrix, aspect=aspect, vmin=vmin, vmax=vmax, **kwargs)
    #ax3.set_xlim([-0.5, matrix.shape[0]+0.5])
    #ax3.set_ylim([-0.5, matrix.shape[1]+0.5])

    if ticklabels is not None:
        ax3.xaxis.set_major_formatter(ticker.IndexFormatter(ticklabels))
        if ncol == 1:
            ax3.yaxis.set_major_formatter(ticker.IndexFormatter(ticklabels))

    if allticks:
        ax3.xaxis.set_major_locator(ticker.IndexLocator(offset=0.5, base=1.))
        ax3.yaxis.set_major_locator(ticker.IndexLocator(offset=0.5, base=1.))
    else:
        ax3.xaxis.set_major_locator(ticker.AutoLocator())
        ax3.xaxis.set_minor_locator(ticker.AutoMinorLocator())

        ax3.yaxis.set_major_locator(ticker.AutoLocator())
        ax3.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    if ncol > 1:
        ax3.yaxis.set_major_formatter(ticker.NullFormatter())
        
    colorbar = None
    if cb:
        if nrow > 1:
            axes = [ax1, ax2, ax3]
            while None in axes:
                axes.remove(None)
            s = H / (H + 1.)
            colorbar = plt.colorbar(mappable=im, ax=axes, anchor=(0, 0), shrink=s)
        else:
            colorbar = plt.colorbar(mappable=im)

    sca(ax3)
    sci(im)
    return im, lines, colorbar

def reorderMatrix(matrix, tree, names=None):
    """
    Reorder a matrix based on a tree and return the reordered matrix 
    and indices for reordering other things.

    :arg names: a list of names associated with the rows of the matrix
        These names must match the ones used to generate the tree.
    :type names: a list of strings

    :arg matrix: any square matrix
    :type matrix: 2D array

    :arg tree: any tree from calcTree
    :type tree: Bio.Phylo.BaseTree.Tree
    """
    try:
        from Bio import Phylo
    except ImportError:
        raise ImportError('Phylo module could not be imported. '
            'Reinstall ProDy or install Biopython '
            'to solve the problem.')

    if not isinstance(matrix, np.ndarray):
        raise TypeError('matrix should be a numpy array.')

    if matrix.ndim != 2:
        raise ValueError('matrix should be a 2D matrix.')

    if np.shape(matrix)[0] != np.shape(matrix)[1]:
        raise ValueError('matrix should be a square matrix')

    if names is None:
        names = [str(i) for i in range(len(matrix))]

    if not isinstance(names, list):
        raise TypeError('names should be a list.')

    if not isinstance(names[0], str):
        raise TypeError('names should be a list of strings.')    

    if not isinstance(tree, Phylo.BaseTree.Tree):
        raise TypeError('tree should be a BioPython Tree')

    if len(names) != len(matrix):
        raise ValueError('names should have entries for each matrix row/column')

    if len(names) != len(tree.get_terminals()):
        raise ValueError('names should have entries for each tree terminal')

    if len(tree.get_terminals()) != len(matrix):
        raise ValueError('matrix should have a row for each tree terminal')

    indices = []
    for terminal in tree.get_terminals():
        indices.append(np.where(np.array(names) == str(terminal.name))[0][0])

    reordered_matrix = matrix[:,indices]
    reordered_matrix = reordered_matrix[indices,:]
    
    return reordered_matrix, indices

def findSubgroups(tree, cutoff=0.8):
    """
    Divide a tree into subgroups using a distance cutoff.
    Returns a list of lists with labels divided into subgroups.
    """

    subgroups = [[]]

    for i, target_i in enumerate(tree.get_terminals()):
        for j, target_j in enumerate(tree.get_terminals()):
            if i == j+1:
                subgroups[-1].append(str(target_j))
                neighbour_distance = tree.distance(target_i,target_j)
                if neighbour_distance > cutoff:
                    subgroups.append([])

    subgroups[-1].append(str(target_j))

    return subgroups

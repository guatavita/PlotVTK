# Created by Bastien Rigaud at 24/01/2022
# Bastien Rigaud, PhD
# Laboratoire Traitement du Signal et de l'Image (LTSI), INSERM U1099
# Campus de Beaulieu, Université de Rennes 1
# 35042 Rennes, FRANCE
# bastien.rigaud@univ-rennes1.fr
# Description:

import numpy as np
import vtk
from vtk.util import numpy_support


def MakeAxesActor(scale, xyzLabels):
    """
    :param scale: Sets the scale and direction of the axes.
    :param xyzLabels: Labels for the axes.
    :return: The axes actor.
    """
    axes = vtk.vtkAxesActor()
    axes.SetScale(scale)
    axes.SetShaftTypeToCylinder()
    axes.SetXAxisLabelText(xyzLabels[0])
    axes.SetYAxisLabelText(xyzLabels[1])
    axes.SetZAxisLabelText(xyzLabels[2])
    axes.SetCylinderRadius(0.5 * axes.GetCylinderRadius())
    axes.SetConeRadius(1.025 * axes.GetConeRadius())
    axes.SetSphereRadius(1.5 * axes.GetSphereRadius())
    tprop = axes.GetXAxisCaptionActor2D().GetCaptionTextProperty()
    tprop.ItalicOn()
    tprop.ShadowOn()
    tprop.SetFontFamilyToTimes()
    # Use the same text properties on the other two axes.
    axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tprop)
    axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tprop)
    return axes


def append_polydata(polydata_list=[]):
    append_filter = vtk.vtkAppendPolyData()
    i = 0
    for poly in polydata_list:
        array_names = [poly.GetPointData().GetArrayName(arrayid) for arrayid in
                       range(poly.GetPointData().GetNumberOfArrays())]
        if 'label_color' not in array_names:
            ntype = numpy_support.get_numpy_array_type(poly.GetPoints().GetDataType())
            label_color = numpy_support.numpy_to_vtk(i * np.ones(poly.GetNumberOfPoints(), dtype=ntype), deep=1)
            label_color.SetName('label_color')
            poly.GetPointData().SetScalars(label_color)
        append_filter.AddInputData(poly)
        i += 1
    append_filter.Update()
    return append_filter.GetOutput()


class KeyPressInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.parent = parent
        self.AddObserver("KeyPressEvent", self.key_press_event)

    def key_press_event(self, obj, event):
        key = self.parent.GetKeySym()
        if key == 'q':
            print('closing PlotVTK window')
            self.close_window()
        return

    def close_window(self):
        render_window = self.parent.GetRenderWindow()
        render_window.Finalize()
        self.parent.TerminateApp()
        del render_window, self.parent


# TODO add dvf with glyph
# TODO add multiview? reference / moving / deformation vector field
def plot_vtk(polydata, secondary=None, opacity=.5):
    '''
    :param polydata: polydata or list of polydata to plot
    :param secondary: secondary polydata or list of polydata for comparison
    :param opacity: opacity of polydata (default: 0.5)
    :return:
    '''

    if isinstance(polydata, list):
        polydata = append_polydata(polydata)

    if isinstance(secondary, list):
        secondary = append_polydata(secondary)

    center_filter = vtk.vtkCenterOfMass()
    center_filter.SetInputData(polydata)
    center_filter.SetUseScalarsAsWeights(False)
    center_filter.Update()
    center = center_filter.GetCenter()
    bounds = polydata.GetBounds()

    # Create camera
    camera = vtk.vtkCamera()
    camera.SetPosition(-5 * (abs(bounds[0] - bounds[1]) / 2), -3 * (abs(bounds[2] - bounds[3]) / 2), 0)
    camera.SetFocalPoint(center[0], center[1], center[2])
    camera.SetViewUp(0, 0, 1)

    colors = vtk.vtkNamedColors()
    scalar_range = polydata.GetScalarRange()

    # Create axes actor
    xyzLabels = ['X', 'Y', 'Z']
    scale = [1.5, -1.5, 1.5]
    axes = MakeAxesActor(scale, xyzLabels)
    om = vtk.vtkOrientationMarkerWidget()
    om.SetOrientationMarker(axes)
    # Position upper left in the viewport.
    om.SetViewport(0, 0, 0.2, 0.2)

    # Create the mapper that corresponds the objects of the vtk file
    # into graphics elements
    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputData(polydata)
    mapper.SetScalarRange(scalar_range)

    # Create the Actor
    actor = vtk.vtkActor()
    actor.GetProperty().SetOpacity(opacity);
    actor.SetMapper(mapper)

    if secondary:
        sec_mapper_ = vtk.vtkDataSetMapper()
        sec_mapper_.SetInputData(secondary)
        sec_mapper_.SetScalarRange(scalar_range)
        sec_actor = vtk.vtkActor()
        sec_actor.GetProperty().SetOpacity(opacity);
        sec_actor.SetMapper(sec_mapper_)

    # Create the Renderer
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(1, 1, 1)  # Set background to white
    renderer.SetActiveCamera(camera)

    # Create the RendererWindow
    renderer_window = vtk.vtkRenderWindow()
    renderer_window.SetWindowName('PlotVTK')
    renderer_window.AddRenderer(renderer)
    renderer_window.SetSize(600, 600)

    # Create the RendererWindowInteractor and display the vtk_file
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renderer_window)
    interactor.SetInteractorStyle(KeyPressInteractorStyle(interactor))

    om.SetInteractor(interactor)
    om.EnabledOn()
    om.InteractiveOff()

    # Add actor to the schene
    renderer.AddActor(actor)
    if secondary:
        renderer.AddActor(sec_actor)

    # add corner annotation
    colors = vtk.vtkNamedColors()
    cornerAnnotation = vtk.vtkCornerAnnotation()
    cornerAnnotation.SetLinearFontScaleFactor(2)
    cornerAnnotation.SetNonlinearFontScaleFactor(1)
    cornerAnnotation.SetMaximumFontSize(20)
    # cornerAnnotation.SetText(0, "lower left")
    cornerAnnotation.SetText(1, "Press key Q to quit")
    # cornerAnnotation.SetText(2, "upper left")
    # cornerAnnotation.SetText(3, "upper right")
    cornerAnnotation.GetTextProperty().SetColor(colors.GetColor3d("Black"))

    # Render and interact
    renderer.AddViewProp(cornerAnnotation)
    renderer_window.Render()
    renderer.GetActiveCamera().Zoom(.8)
    renderer_window.Render()

    interactor.Initialize()
    renderer_window.Render()
    interactor.Start()

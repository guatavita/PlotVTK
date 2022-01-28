# Created by Bastien Rigaud at 24/01/2022
# Bastien Rigaud, PhD
# Laboratoire Traitement du Signal et de l'Image (LTSI), INSERM U1099
# Campus de Beaulieu, Université de Rennes 1
# 35042 Rennes, FRANCE
# bastien.rigaud@univ-rennes1.fr
# Description:

import numpy as np
import vtk
from numpy import poly1d
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
        temp = vtk.vtkPolyData()
        temp.DeepCopy(poly)
        array_names = [temp.GetPointData().GetArrayName(arrayid) for arrayid in
                       range(temp.GetPointData().GetNumberOfArrays())]
        if 'label_color' not in array_names:
            label_color = numpy_support.numpy_to_vtk(i * np.ones(temp.GetNumberOfPoints()))
            label_color.SetName('label_color')
            temp.GetPointData().AddArray(label_color)
            temp.GetPointData().SetActiveScalars('label_color')
        append_filter.AddInputData(temp)
        i += 1
    append_filter.Update()
    return append_filter.GetOutput()


class KeyPressInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, parent, mapper, actor, glyph_actor=None):
        self.parent = parent
        self.mapper = mapper
        self.actor = actor
        self.glyph_actor = glyph_actor
        self.glyph_opacity = glyph_actor.GetProperty().GetOpacity() if glyph_actor else 0.0
        self.polydata = vtk.vtkPolyData()
        self.polydata.DeepCopy(mapper.GetInput())
        self.warp_filter = vtk.vtkWarpVector()
        self.warp_step = 5
        self.warp_sign = 1
        self.warp_factor = 0
        self.opacity_factor = 100*self.actor.GetProperty().GetOpacity()
        self.opacity_sign = 1
        self.opacity_step = 10
        self.array_names = [self.polydata.GetPointData().GetArrayName(arrayid) for arrayid in
                            range(self.polydata.GetPointData().GetNumberOfArrays())]+[None]
        self.index_scalar = 0
        self.AddObserver("KeyPressEvent", self.key_press_event)

    def key_press_event(self, obj, event):
        key = self.parent.GetKeySym()
        if key == 'q':
            print(' PlotVTK: closing PlotVTK window')
            self.close_window()
        if key == 't':
            if len(self.array_names) == 0:
                print(' PlotVTK: no scalars found')
                return
            self.index_scalar += 1
            if self.index_scalar == len(self.array_names):
                self.index_scalar = 0
            print(' PlotVTK: changing scalar to {}'.format(self.array_names[self.index_scalar]))
            if self.array_names[self.index_scalar]:
                self.mapper.ScalarVisibilityOn()
                self.mapper.GetInput().GetPointData().SetActiveScalars(self.array_names[self.index_scalar])
                self.mapper.SetScalarRange(self.polydata.GetPointData().GetArray(self.index_scalar).GetRange())
            else:
                self.mapper.ScalarVisibilityOff()
        if key == 'g':
            if not self.glyph_actor:
                print(' PlotVTK: no vectors found')
                return
            current_opacity = self.glyph_actor.GetProperty().GetOpacity()
            self.glyph_actor.GetProperty().SetOpacity(abs(current_opacity - self.glyph_opacity))
        if key == 'd':
            if not self.glyph_actor:
                print(' PlotVTK: no vectors found')
                return
            self.warp_factor = self.warp_factor+self.warp_sign*self.warp_step
            if self.warp_factor == 100 or self.warp_factor == 0:
                self.warp_sign = -1*self.warp_sign
            print(' PlotVTK: warp scale factor {}%'.format(self.warp_factor))
            self.warp_filter.SetInputData(self.polydata)
            self.warp_filter.SetScaleFactor(self.warp_factor / 100)
            self.warp_filter.Update()
            self.mapper.SetInputData(self.warp_filter.GetOutput())
        if key == 'o':
            self.opacity_factor = self.opacity_factor+self.opacity_sign*self.opacity_step
            print(' PlotVTK: opacity to {}%'.format(self.opacity_factor))
            if self.opacity_factor == 100 or self.opacity_factor == 0:
                self.opacity_sign = -1*self.opacity_sign
            self.actor.GetProperty().SetOpacity(self.opacity_factor/100)
        render_window = self.parent.GetRenderWindow()
        render_window.Render()
        return

    def close_window(self):
        render_window = self.parent.GetRenderWindow()
        render_window.Finalize()
        self.parent.TerminateApp()
        del render_window, self.parent

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
    mapper.SetScalarRange(polydata.GetScalarRange())

    # Create the Actor
    actor = vtk.vtkActor()
    actor.GetProperty().SetOpacity(opacity)
    actor.SetMapper(mapper)

    if secondary:
        sec_mapper = vtk.vtkDataSetMapper()
        sec_mapper.SetInputData(secondary)
        sec_mapper.SetScalarRange(secondary.GetScalarRange())
        sec_actor = vtk.vtkActor()
        sec_actor.GetProperty().SetOpacity(opacity)
        sec_actor.SetMapper(sec_mapper)

    if polydata.GetPointData().GetVectors():
        # Set up the glyph filter
        glyph = vtk.vtkGlyph3D()
        glyph_mapper = vtk.vtkDataSetMapper()
        glyph_actor = vtk.vtkActor()
        # define glyph filter
        glyph.SetInputData(polydata)
        glyph.SetScaleModeToScaleByVector()
        glyph.Update()
        # define glyph mapper and actor
        glyph_mapper = vtk.vtkDataSetMapper()
        glyph_mapper.SetInputConnection(glyph.GetOutputPort())
        glyph_actor = vtk.vtkActor()
        glyph_actor.GetProperty().SetOpacity(0.1)
        glyph_actor.SetMapper(glyph_mapper)
    else:
        glyph_actor = None

    # Scalar bar actor
    scalar_bar = vtk.vtkScalarBarActor()
    scalar_bar.SetLookupTable(mapper.GetLookupTable())
    # scalar_bar.SetTitle("")
    scalar_bar.SetNumberOfLabels(4)
    # scalar_bar.SetBarRatio(0.3)
    # scalar_bar.SetHeight(0.3)
    scalar_bar.SetOrientationToHorizontal()
    scalar_bar.SetPosition(0,0.5)
    text_property = vtk.vtkTextProperty()
    text_property.SetColor(0, 0, 0)
    # text_property.SetFontSize(12)
    text_property.SetItalic(False)
    text_property.SetShadow(False)
    scalar_bar.SetLabelTextProperty(text_property)
    scalar_bar.SetAnnotationTextProperty(text_property)
    scalar_bar.SetTitleTextProperty(text_property)

    # Create the Renderer
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(1, 1, 1)  # Set background to white
    renderer.SetActiveCamera(camera)

    # Create the RendererWindow
    renderer_window = vtk.vtkRenderWindow()
    renderer_window.SetWindowName('PlotVTK')
    renderer_window.AddRenderer(renderer)
    renderer_window.SetSize(800, 800)

    # Create the RendererWindowInteractor and display the vtk_file
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renderer_window)
    interactor.SetInteractorStyle(KeyPressInteractorStyle(interactor, mapper, actor, glyph_actor))

    om.SetInteractor(interactor)
    om.EnabledOn()
    om.InteractiveOff()

    # Add actor to the schene
    renderer.AddActor(actor)
    if secondary:
        renderer.AddActor(sec_actor)
    renderer.AddActor(glyph_actor)
    renderer.AddActor2D(scalar_bar)

    # add corner annotation
    cornerAnnotation = vtk.vtkCornerAnnotation()
    cornerAnnotation.SetLinearFontScaleFactor(2)
    cornerAnnotation.SetNonlinearFontScaleFactor(1)
    cornerAnnotation.SetMaximumFontSize(20)
    # cornerAnnotation.SetText(0, "lower left")
    cornerAnnotation.SetText(1, "{}\n{}\n{}\n{}\n{}\n{}".format('Press key:', 'T to toggle scalars',
                                                                'G to toggle glyphs', 'D to deform (5%)',
                                                                'O for opacity (10%)', 'Q to quit'))
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

True = 1
False = 0

import ctypes

SDL_INIT_VIDEO = 0x00000020
SDL_OPENGL = 0x00000002
SDL_GL_DOUBLEBUFFER = 5

sdl = ctypes.CDLL("libSDL.so")
gl = ctypes.CDLL("libGL.so")

GL_TRIANGLES = 0x0004

sdl.SDL_Init(SDL_INIT_VIDEO)

sdl.SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1)

sdl.SDL_SetVideoMode( 640, 480, 32, SDL_OPENGL | SDL_GL_DOUBLEBUFFER )

#gl.glColor3f.argtypes = ctypes.c_float, ctypes.c_float, ctypes.c_float
#gl.glVertex2f.argtypes = ctypes.c_float, ctypes.c_float

while True:
    gl.glBegin(GL_TRIANGLES)
    gl.glColor3d(1., 0., 0.)
    gl.glVertex2d(.1, .1)
    gl.glVertex2d(.2, .1)
    gl.glVertex2d(.1, .2)
    gl.glEnd()
    sdl.SDL_GL_SwapBuffers()

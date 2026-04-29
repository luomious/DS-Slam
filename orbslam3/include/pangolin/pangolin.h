#ifndef PANGOLIN_STUB_H
#define PANGOLIN_STUB_H

// Stub header for Pangolin when visualization is disabled
// Provides minimal types needed for compilation

#include <Eigen/Core>
#include <GL/gl.h>

namespace pangolin {

// Minimal OpenGlMatrix stub
struct OpenGlMatrix {
    double m[16];
    OpenGlMatrix() {
        for(int i = 0; i < 16; i++) m[i] = (i % 5 == 0) ? 1.0 : 0.0;
    }
    void SetIdentity() {
        for(int i = 0; i < 16; i++) m[i] = (i % 5 == 0) ? 1.0 : 0.0;
    }
};

} // namespace pangolin

// Stub OpenGL types
#ifndef GLubyte
#define GLubyte unsigned char
#endif

#ifndef GLuint
#define GLuint unsigned int
#endif

#ifndef GLfloat
#define GLfloat float
#endif

#endif // PANGOLIN_STUB_H

/*
    This is a test program illustrating Bloomenthal's implicit surface
    polygonizer in its new C++ guise.

    J. Andreas Bærentzen 2003.
*/




#include "polygonizer.h"
#include <cmath>
#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <algorithm>
#include <memory>
#include <GL/glut.h>
#include <cassert>

using namespace std;




typedef std::unique_ptr<ImplicitFunction> childPtr;

class Torus: public ImplicitFunction {
    float eval (float x, float y, float z) {
        float x2 = x*x, y2 = y*y, z2 = z*z;
        float a = x2+y2+z2+(0.5*0.5)-(0.1*0.1);
        return -(a*a-4.0*(0.5*0.5)*(y2+z2));
    }
};

const float pow2 = logf(2.0)/logf(M_E);

// trim from start
static inline std::string &ltrim(std::string &s) {
        s.erase(s.begin(), std::find_if(s.begin(), s.end(), std::not1(std::ptr_fun<int, int>(std::isspace))));
        return s;
}
// trim from end
static inline std::string &rtrim(std::string &s) {
        s.erase(std::find_if(s.rbegin(), s.rend(), std::not1(std::ptr_fun<int, int>(std::isspace))).base(), s.end());
        return s;
}
// trim from both ends
static inline std::string &trim(std::string &s) {
        return ltrim(rtrim(s));
}


float clampf(float v, float min, float max) {
    if (v < min) v = min;
    if (v > max) v = max;
    return v;
}

bool whiteSpaceOrComment(string &line);  // forward declaration

/* sphere: an inverse square function (always positive) */
class Sphere: public ImplicitFunction {
    public:
        float radius;
        Sphere() : radius(1) { }
        Sphere(float radius_) : radius(radius_) { }

        Sphere(ifstream &file) {
            string line;
            while ( getline(file,line) ) {
                // skip unwanted things
                trim(line);
                if (line == ")") {                      break;      }
                else if (whiteSpaceOrComment(line)) {   continue;   }

                radius = stof(line);
            }
        }

        virtual float eval (float x, float y, float z) {
            float dist = sqrtf(x*x+y*y+z*z);
            // return expf(-pow2 * (x*x+y*y+z*z) / (radius*radius));
            // return max(0.f, 2*radius - dist);
            // return .5 * (1 + cosf(clampf(dist * M_PI/(2.0*radius), -M_PI, M_PI)));

            float cosBump = .5 * (1 + cosf(clampf(dist * M_PI/(3.0*radius), -M_PI, M_PI)));
            cosBump = cosBump * cosBump * cosBump;
            return cosBump;

        }
};


class Constant: public ImplicitFunction {
    public:
        float value;

        Constant(ifstream &file) : value(0.5) {
            string line;
            while (getline(file,line)) {
                // skip unwanted things
                trim(line);
                if (line == ")") {                      break;      }
                else if (whiteSpaceOrComment(line)) {   continue;   }


                value = stof(line);
            }
        }

        virtual float eval(float x, float y, float z) {
            return value;
        }
};

// forward declatation
class Container: public ImplicitFunction {
    public:
        std::vector<childPtr> children;
        void init(ifstream &file);
        virtual void parseDefault(string &line);
        float eval(float x, float y, float z);
        virtual float evalChild(const childPtr &child, float x, float y, float z);
};


class Translate: public Container {
public:
    float tx, ty, tz;

    Translate(ifstream &file) : tx(0.0), ty(0.0), tz(0.0) {
        init(file);
    }

    virtual void parseDefault(string &line) {
        istringstream iss(line);
        if (!( iss >> tx )) { throw "parsing error: " + line;   }
        if (!( iss >> ty )) { throw "parsing error: " + line;   }
        if (!( iss >> tz )) { throw "parsing error: " + line;   }
    }

    virtual float evalChild(const childPtr &child, float x, float y, float z) {
        return child->eval(
            x - tx,
            y - ty,
            z - tz
        );
    }

};

class Negate: public Container {
public:

    Negate(ifstream &file) {
        init(file);
    }

    virtual float evalChild(const childPtr &child, float x, float y, float z) {
        return - child->eval(x,y,z);
    }

};



// Container implementation
void Container::init(ifstream &file) {
    children.clear();
    string line;
    while ( getline(file,line) ) {
        trim(line);
        if (line == ")") {                      break;      }
        else if (whiteSpaceOrComment(line)) {   continue;   }
        else if (line == "Constant("    ) { children.push_back(childPtr(new    Constant(file)));  }
        else if (line == "Sphere("      ) { children.push_back(childPtr(new      Sphere(file)));  }
        else if (line == "Translate("   ) { children.push_back(childPtr(new   Translate(file)));  }
        else if (line == "Negate("      ) { children.push_back(childPtr(new      Negate(file)));  }
        else {
            parseDefault(line);
        }
    }
}
void Container::parseDefault(string &line) {
    throw "Encountered unknown ImplicitFunction: " + line;
}
float Container::eval(float x, float y, float z) {
    float sum = 0;
    for (const childPtr &child : children) {
        sum += evalChild(child, x, y, z);
    }
    return sum;
}
float Container::evalChild(const childPtr &child, float x, float y, float z) {
    return child->eval(x,y,z);
}



/* blob: a three-pole blend function, try size = .1 */
class Blob: public ImplicitFunction {
    public:
        virtual float eval (float x, float y, float z) {
            Sphere sphere(0.13);
            return sphere.eval(x,y,z)
                +sphere.eval(x,y+0.3,z)
                +sphere.eval(x,y,z+0.3)
                -0.5f
                ;
        }
};




namespace
{
    bool dotet=true;
    float polygonSpacing = 0.07;
    const float polygonBounds = 300.0;
    const bool wireframe = false;

    bool continousReload = true;
    Container root;
    string inputFilePath;
}










bool whiteSpaceOrComment(string &line) {
    if (line == "") return true;
    else if (line.at(0) == '#') {
        if (line.find("#SETVAR polygonSpacing") == 0) {
            string numberString = line.substr(23, 10);
            polygonSpacing = stof(numberString);
        }
        return true;
    }
    return false;
}

void loadInputFile() {
    ifstream file(inputFilePath);
    try {
        root.init(file);
    }
    catch (string& s) {
        std::cout << "parsing error: \"" << s << "\"" << endl;
        throw s;
    }
    file.close();
}

void marchPolygonizer(Polygonizer &pol) {
    try {
        pol.march(dotet, 0.,0.,0.);
    }
    catch (string& s) {
        std::cout << "polygonizer error: \"" << s << "\"" << endl;
        // throw s;
    }

}

void display()
{
    static int iter=0;
    glClear(GL_DEPTH_BUFFER_BIT|GL_COLOR_BUFFER_BIT);

    // Blob blob;
    // Torus torus;


    if (continousReload) {
        loadInputFile();
    }
    Polygonizer pol(&root, polygonSpacing, polygonBounds);
    marchPolygonizer(pol);

    glPushMatrix();
    glRotatef(iter, 0,1,0);
    iter++;

    for(int i=0;i<pol.no_triangles(); ++i)
        {
            TRIANGLE t = pol.get_triangle(i);
            glBegin(GL_TRIANGLES);
                NORMAL n0 = pol.get_normal(t.v0);
                glNormal3f(n0.x, n0.y, n0.z);
                VERTEX v0 = pol.get_vertex(t.v0);
                glVertex3f(v0.x, v0.y, v0.z);

                NORMAL n1 = pol.get_normal(t.v1);
                glNormal3f(n1.x, n1.y, n1.z);
                VERTEX v1 = pol.get_vertex(t.v1);
                glVertex3f(v1.x, v1.y, v1.z);

                NORMAL n2 = pol.get_normal(t.v2);
                glNormal3f(n2.x, n2.y, n2.z);
                VERTEX v2 = pol.get_vertex(t.v2);
                glVertex3f(v2.x, v2.y, v2.z);
            glEnd();
        }

    if (wireframe) {
        glDisable(GL_LIGHTING);
        glPolygonOffset(-1,-1);
        glEnable(GL_POLYGON_OFFSET_LINE);
        glPolygonMode(GL_FRONT_AND_BACK,GL_LINE);
        glColor3f(1,0,0);
        for(int i=0;i<pol.no_triangles(); ++i)
            {
                TRIANGLE t = pol.get_triangle(i);
                glBegin(GL_TRIANGLES);
                    NORMAL n0 = pol.get_normal(t.v0);
                    glNormal3f(n0.x, n0.y, n0.z);
                    VERTEX v0 = pol.get_vertex(t.v0);
                    glVertex3f(v0.x, v0.y, v0.z);

                    NORMAL n1 = pol.get_normal(t.v1);
                    glNormal3f(n1.x, n1.y, n1.z);
                    VERTEX v1 = pol.get_vertex(t.v1);
                    glVertex3f(v1.x, v1.y, v1.z);

                    NORMAL n2 = pol.get_normal(t.v2);
                    glNormal3f(n2.x, n2.y, n2.z);
                    VERTEX v2 = pol.get_vertex(t.v2);
                    glVertex3f(v2.x, v2.y, v2.z);
                glEnd();
            }
        glEnable(GL_LIGHTING);
        glDisable(GL_POLYGON_OFFSET_LINE);
        glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);
    }

    glPopMatrix();
    glutSwapBuffers();
}

void idle()
{
    glutPostRedisplay();
}

int main (int argc, char** argv)
{
    int inputFileIndex = 1;
    if (argc>1 && string(argv[1])=="-C") {
        dotet = false;
        inputFileIndex += 1;
    }


    // input handling
    if (argc <= inputFileIndex) {
        std::cerr << "I require a input file" << std::endl;
        return 0;
    }
    inputFilePath = argv[inputFileIndex];
    loadInputFile();



    // output handling
    // we either write to file or make a GUI
    if (argc == inputFileIndex+2) {
        // we got and output file path
        // lets write our polygonization to that file as an .obj

        Polygonizer pol(&root, polygonSpacing, polygonBounds);
        marchPolygonizer(pol);

        string outFilePath = argv[inputFileIndex+1];
        ofstream outFile(outFilePath);
        if (outFile.is_open()) {
            outFile << "g bloomy \n\n";

            // vertices
            for (int i=0;i<pol.no_vertices(); ++i) {
                VERTEX &vertex = pol.get_vertex(i);
                outFile << "v "
                    << vertex.x << "\t"
                    << vertex.y << "\t"
                    << vertex.z << "\n";
            }

            string separator = "\n\n\n";
            outFile << separator;

            // normals
            for (int i=0;i<pol.no_normals(); ++i) {
                NORMAL &normal = pol.get_normal(i);
                outFile << "vn "
                    << -normal.x << "\t"
                    << -normal.y << "\t"
                    << -normal.z << "\n";
            }

            outFile << separator;

            // faces
            for (int i=0;i<pol.no_triangles(); ++i) {
                TRIANGLE triangle = pol.get_triangle(i);
                outFile << "f "
                    << triangle.v0 + 1 << "//" << triangle.v0 + 1  << "\t"
                    << triangle.v1 + 1 << "//" << triangle.v1 + 1  << "\t"
                    << triangle.v2 + 1 << "//" << triangle.v2 + 1  << "\n";
            }

            outFile.close();
            cout << "sucessfully wrote to file: " << outFilePath << endl;
        }
        else {
            cout << "Unable to open output file: " << outFilePath << endl;
        }

    }
    else {

        // create the GUI
        glutInit(&argc,argv);
        glutInitDisplayMode(GLUT_RGBA|GLUT_DEPTH|GLUT_DOUBLE);
        glutInitWindowSize(500,500);
        glutCreateWindow("Bloomenthal Polygonizer");
        glutDisplayFunc(display);
        glutIdleFunc(idle);

        glEnable(GL_LIGHTING);
        glEnable(GL_LIGHT0);
        glEnable(GL_DEPTH_TEST);
        glEnable(GL_NORMALIZE);
        glShadeModel(GL_SMOOTH);
        glutMainLoop();
    }
    return 0;
}

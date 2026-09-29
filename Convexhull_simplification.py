#####directly copy from SILD_convexhull_simplification-minimize_adding_volume_or_normalized_adding_volume.ipynb 2016.01.11
#### and then remove many unrelated codes. 

from __future__ import print_function, division

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial import Delaunay
from scipy.optimize import *
from math import *
## cvxopt (with GLPK) and PIL are optional so that this also runs in the browser (Pyodide).
## Without cvxopt, we fall back to scipy's HiGHS linear programming solver.
try: import cvxopt
except ImportError: cvxopt = None
try: import PIL.Image as Image
except ImportError: Image = None
import sys    

######***********************************************************************************************

#### 3D case: use method in paper: "Progressive Hulls for Intersection Applications"
#### also using trimesh.py interface from yotam gingold

def visualize_hull(hull,groundtruth_hull=None):
    from matplotlib import pyplot as plt
    
    fig = plt.figure(figsize=(8,8))
    ax = fig.add_subplot(1,1,1, projection='3d')
    vertex=hull.points[hull.vertices]
    ax.scatter(vertex[:,0], vertex[:,1], vertex[:,2], 
       marker='*', color='red', s=40, label='class')
    
#     num=hull.simplices.shape[0]
#     points=[]
#     normals=[]
#     for i in range(num):
#         face=hull.points[hull.simplices[i]]
#         avg_point=(face[0]+face[1]+face[2])/3.0
#         points.append(avg_point)
#     points=np.asarray(points)
    
#     ax.quiver(points[:,0],points[:,1],points[:,2],hull.equations[:,0],hull.equations[:,1],hull.equations[:,2],length=0.01)
    
    for simplex in hull.simplices:
        faces=hull.points[simplex]
        xs=list(faces[:,0])
        xs.append(faces[0,0])
        ys=list(faces[:,1])
        ys.append(faces[0,1])
        zs=list(faces[:,2])
        zs.append(faces[0,2])
#         print xs,ys,zs
        plt.plot(xs,ys,zs,'k-')

    if groundtruth_hull!=None:
        groundtruth_vertex=groundtruth_hull.points[groundtruth_hull.vertices]
        ax.scatter(groundtruth_vertex[:,0], groundtruth_vertex[:,1], groundtruth_vertex[:,2], 
           marker='o', color='green', s=80, label='class')
    
    plt.title("3D Scatter Plot")
    plt.show()
    
    
    
    
from trimesh import TriMesh

def write_convexhull_into_obj_file(hull, output_rawhull_obj_file):
    hvertices=hull.points[hull.vertices]
    points_index=-1*np.ones(hull.points.shape[0],dtype=np.int32)
    points_index[hull.vertices]=np.arange(len(hull.vertices))
    #### start from index 1 in obj files!!!!!
    hfaces=np.array([points_index[hface] for hface in hull.simplices])+1
    
    #### to make sure each faces's points are countclockwise order.
    for index in range(len(hfaces)):
        face=hvertices[hfaces[index]-1]
        normals=hull.equations[index,:3]
        p0=face[0]
        p1=face[1]
        p2=face[2]
        
        n=np.cross(p1-p0,p2-p0)
        if np.dot(normals,n)<0:
            hfaces[index][[1,0]]=hfaces[index][[0,1]]
            
    myfile=open(output_rawhull_obj_file,'w')
    for index in range(hvertices.shape[0]):
        myfile.write('v '+str(hvertices[index][0])+' '+str(hvertices[index][1])+' '+str(hvertices[index][2])+'\n')
    for index in range(hfaces.shape[0]):
        myfile.write('f '+str(hfaces[index][0])+' '+str(hfaces[index][1])+' '+str(hfaces[index][2])+'\n')
    myfile.close()

    


def edge_normal_test(vertices, faces, old_face_index_list, v0_ind, v1_ind):
    selected_old_face_list=[]
    central_two_face_list=[]
    
    for index in old_face_index_list:
        face=faces[index]
        face_temp=np.array(face).copy()
        face_temp=list(face_temp)
        
        if v0_ind in face_temp:
            face_temp.remove(v0_ind)
        if v1_ind in face_temp:
            face_temp.remove(v1_ind)
        if len(face_temp)==2:  ### if left 2 points, then this face is what we need.
            selected_old_face=[np.asarray(vertices[face[i]]) for i in range(len(face))]
            selected_old_face_list.append(np.asarray(selected_old_face))
        if len(face_temp)==1: ##### if left 1 points, then this face is central face.
            central_two_face=[np.asarray(vertices[face[i]]) for i in range(len(face))]
            central_two_face_list.append(np.asarray(central_two_face))
            
    assert( len(central_two_face_list)==2 )
    if len(central_two_face_list)+len(selected_old_face_list)!=len(old_face_index_list):
        print ('error!!!!!!')
    
    central_two_face_normal_list=[]
    neighbor_face_dot_normal_list=[]
    
    for face in central_two_face_list:
        n=np.cross(face[1]-face[0], face[2]-face[0])
        n=n/np.sqrt(np.dot(n,n))
        central_two_face_normal_list.append(n)
        
    avg_edge_normal=np.average(np.array(central_two_face_normal_list),axis=0)
    
    for face in selected_old_face_list:
        n=np.cross(face[1]-face[0], face[2]-face[0])
        neighbor_face_dot_normal_list.append(np.dot(avg_edge_normal,n))
    
    if (np.array(neighbor_face_dot_normal_list)>=0.0-1e-5).all():
        return 1
    else:
        return 0


        
def compute_tetrahedron_volume(face, point):
    n=np.cross(face[1]-face[0], face[2]-face[0])
    return abs(np.dot(n, point-face[0]))/6.0




def solve_lp( c, A, b ):
    '''
    Minimize c*x w.r.t. A*x<=b with x unbounded.
    Returns the optimal x, or None if the problem has no optimal solution.
    '''
    if cvxopt is not None:
        cvxopt.solvers.options['show_progress'] = False
        cvxopt.solvers.options['glpk'] = dict(msg_lev='GLP_MSG_OFF')
        res = cvxopt.solvers.lp( cvxopt.matrix(c), cvxopt.matrix(A), cvxopt.matrix(b), solver='glpk' )
        if res['status']=='optimal':
            return np.asarray( res['x'], dtype=float ).squeeze()
        return None
    else:
        import scipy.optimize
        res = scipy.optimize.linprog( c, A_ub=A, b_ub=b, bounds=(None,None), method='highs' )
        if res.status==0:
            return res.x
        return None


#### this is different from function: remove_one_edge_by_finding_smallest_adding_volume(mesh)
#### add some test conditions to accept new vertex.
#### if option ==1, return a new convexhull.
#### if option ==2, return a new mesh (using trimesh.py)
#### lp_cache is an optional dictionary that caches linear programming solutions across calls.
#### Pass the same dictionary when calling this repeatedly on a simplifying mesh;
#### most edges' neighborhoods are unchanged from one call to the next.
def remove_one_edge_by_finding_smallest_adding_volume_with_test_conditions(mesh, option, lp_cache=None):
 
    edges=mesh.get_edges()
    mesh.get_halfedges()
    faces=mesh.faces
    vertices=mesh.vs
#     print (len(vertices))
    vertex_positions=np.asarray(vertices, dtype=float)
    face_array=np.asarray(faces, dtype=int)
    
    temp_list1=[]
    temp_list2=[]
    count=0

    for edge_index in range(len(edges)):
        
        edge=edges[edge_index]
        vertex1=edge[0]
        vertex2=edge[1]
        face_index1=mesh.vertex_face_neighbors(vertex1)
        face_index2=mesh.vertex_face_neighbors(vertex2)

        face_index=list(set(face_index1) | set(face_index2))
        ## The related faces' vertex positions, as a len(face_index)-by-3-by-3 array.
        old_faces=vertex_positions[ face_array[ face_index ] ]
        
        
        #### now find a point, so that for each face in related_faces will create a positive volume tetrahedron using this point.
        ### minimize c*x. w.r.t. A*x<=b
        ## Vectorized over faces, since this loop is the bottleneck (particularly in the browser).
        p0=old_faces[:,0]
        unnormalized_n=np.cross(old_faces[:,1]-p0, old_faces[:,2]-p0)
        
        #### Currently use this line. without this line, test_fourcolors results are not good.
        n=unnormalized_n/np.sqrt((unnormalized_n**2).sum(axis=1))[:,None] ##### use normalized face normals means distance, not volume
        
        A=n
        b=(n*p0).sum(axis=1)
        c=n.sum(axis=0)

########### now use cvxopt.solvers.lp solver
            
        A=-A
        b=-b
        
        if lp_cache is None:
            newpoint = solve_lp( c, A, b )
        else:
            ## Sort the constraints so that the same neighborhood always produces the same key.
            order = np.lexsort( np.column_stack( ( A, b ) ).T )
            A = A[order]
            b = b[order]
            key = A.tobytes() + b.tobytes()
            if key not in lp_cache:
                lp_cache[key] = solve_lp( c, A, b )
            newpoint = lp_cache[key]

        if newpoint is not None:
        

            ######## using objective function to calculate (volume) or (distance to face) as priority.
#             volume=res['primal objective']+b.sum()
            
    
            ####### manually compute volume as priority,so no relation with objective function
            ## This is compute_tetrahedron_volume() summed over old_faces.
            volume=np.abs((unnormalized_n*(newpoint-p0)).sum(axis=1)).sum()/6.0
            


            temp_list1.append((count, volume, vertex1, vertex2))
            temp_list2.append(newpoint)
            count+=1
           
        # else:
        #     # print 'cvxopt.solvers.lp is not optimal ', res['status'], np.asfarray( res['x'] ).squeeze()
        #     if res['status']!='unknown': ### means solver failed
        #         ##### check our test to see if the solver fails normally
        #         if edge_normal_test(vertices,faces,face_index,vertex1,vertex2)==1: ### means all normal dot value are positive
        #             print '!!!edge_normal_neighbor_normal_dotvalue all positive, but solver fails'
              
    # print ("WHY3")  

    if option==1:
        if len(temp_list1)==0:
            print ('all fails')
            hull=ConvexHull(mesh.vs)
        else:
            min_tuple=min(temp_list1,key=lambda x: x[1])
            # print min_tuple
            final_index=min_tuple[0]
            final_point=temp_list2[final_index]
            # print 'final_point ', final_point
            new_total_points=mesh.vs
            new_total_points.append(final_point)

            hull=ConvexHull(np.array(new_total_points))
        return hull
    
    if option==2:
        
        if len(temp_list1)==0:
            # print 'all fails'
            pass
        else:
            min_tuple=min(temp_list1,key=lambda x: x[1])
            # print min_tuple
            final_index=min_tuple[0]
            final_point=temp_list2[final_index]
            # print 'final_point ', final_point
            
            v1_ind=min_tuple[2]
            v2_ind=min_tuple[3]

            ## Collect all faces touching the edge (either vertex).
            face_index1=mesh.vertex_face_neighbors(v1_ind)
            face_index2=mesh.vertex_face_neighbors(v2_ind)
            face_index=list(set(face_index1) | set(face_index2))
            ## Collect the vertices of all faces touching the edge.
            related_faces_vertex_ind=[faces[index] for index in face_index]

            ## Check link conditions. If link conditions are violated, the resulting
            ## mesh wouldn't be manifold.
            if len( (set(mesh.vertex_vertex_neighbors(v1_ind)).intersection(set(mesh.vertex_vertex_neighbors(v2_ind)))) ) != 2:
                print( "Link condition violated. Should not remove edge." )
            
            ## Remove the edge's two vertices.
            ## This also removes faces attached to either vertex.
            ## All other vertices have new indices.
            old2new=mesh.remove_vertex_indices([v1_ind, v2_ind])
            
            ## The edge will collapse to a new vertex.
            ## That new vertex will be at the end.
            new_vertex_index=current_vertices_num=len(old2new[old2new!=-1])
            
            ## Fill the hole in the mesh by re-attaching
            ## all the deleted faces to either removed vertex
            ## to the new vertex.
            new_faces_vertex_ind=[]
            
            for face in related_faces_vertex_ind:
                ## Map old vertex indices to new ones.
                ## The removed vertices both collapse to the new vertex index.
                new_face=[new_vertex_index if x==v1_ind or x==v2_ind else old2new[x] for x in face]
                ## The two faces on either side of the collapsed edge will be degenerate.
                ## Two vertices in those faces will both be the same vertex (the new one).
                ## Don't add that face.
                if len(set(new_face))==len(new_face):
                    new_faces_vertex_ind.append(new_face)
            
            
            ## Add the new vertex.
            ##### do not clip coordinates to[0,255]. when simplification done, clip.
            mesh.vs = np.vstack( ( mesh.vs, final_point ) )
            

            ##### clip coordinates during simplification!
            # mesh.vs.append(final_point.clip(0.0,255.0))
            

            ## Add the new faces.
            # for face in new_faces_vertex_ind: mesh.faces.append(face)
            mesh.faces = np.vstack( ( mesh.faces, new_faces_vertex_ind ) )
            
            ## Tell the mesh to regenerate the half-edge data structure.
            mesh.topology_changed()

            # print (len(mesh.vs))
    
        return mesh
        
    
    
    
    

############### using original image as input###############



if __name__=="__main__":

   
    input_image_path=sys.argv[1]+".png"
    output_rawhull_obj_file=sys.argv[1]+"-rawconvexhull.obj"
    js_output_file=sys.argv[1]+"-final_simplified_hull.js"
    js_output_clip_file=sys.argv[1]+"-final_simplified_hull_clip.js"
    js_output_file_origin=sys.argv[1]+"-original_hull.js"
    E_vertice_num=4


    import time 
    start_time=time.clock()

    images=np.asarray(Image.open(input_image_path).convert('RGB'), dtype=float).reshape((-1,3))
    hull=ConvexHull(images)
    origin_hull=hull
    # visualize_hull(hull)
    write_convexhull_into_obj_file(hull, output_rawhull_obj_file)




    N=500
    mesh=TriMesh.FromOBJ_FileName(output_rawhull_obj_file)
    print ('original vertices number:',len(mesh.vs))


    for i in range(N):

        print ('loop:', i)
        
        old_num=len(mesh.vs)
        mesh=TriMesh.FromOBJ_FileName(output_rawhull_obj_file)
        mesh=remove_one_edge_by_finding_smallest_adding_volume_with_test_conditions(mesh,option=2)
        newhull=ConvexHull(mesh.vs)
        write_convexhull_into_obj_file(newhull, output_rawhull_obj_file)

        print ('current vertices number:', len(mesh.vs))

        if len(newhull.vertices) <= 10:
            import json, os
            name = os.path.splitext( js_output_file )[0] + ( '-%02d.js' % len(newhull.vertices ))
            with open( name, 'w' ) as myfile:
                json.dump({'vs': newhull.points[ newhull.vertices ].tolist(),'faces': newhull.points[ newhull.simplices ].tolist()}, myfile, indent = 4 )
            
            name = os.path.splitext( js_output_clip_file )[0] + ( '-%02d.js' % len(newhull.vertices ))
            with open( name, 'w' ) as myfile:
                json.dump({'vs': newhull.points[ newhull.vertices ].clip(0.0,255.0).tolist(),'faces': newhull.points[ newhull.simplices ].clip(0.0,255.0).tolist()}, myfile, indent = 4 )
            
            pigments_colors=newhull.points[ newhull.vertices ].clip(0,255).round().astype(np.uint8)
            pigments_colors=pigments_colors.reshape((pigments_colors.shape[0],1,pigments_colors.shape[1]))
            Image.fromarray( pigments_colors ).save( os.path.splitext( js_output_clip_file )[0] + ( '-%02d.png' % len(newhull.vertices )) )


        if len(mesh.vs)==old_num or len(mesh.vs)<=E_vertice_num:
            print ('final vertices number', len(mesh.vs))
            break

            
                
    newhull=ConvexHull(mesh.vs)
    # visualize_hull(newhull)
    write_convexhull_into_obj_file(newhull, output_rawhull_obj_file) 
    # print (newhull.points[newhull.vertices])


    # import json
    # with open( js_output_file, 'w' ) as myfile:
    #     json.dump({'vs': newhull.points[ newhull.vertices ].tolist(),'faces': newhull.points[ newhull.simplices ].tolist()}, myfile, indent = 4 )

    with open( js_output_file_origin, 'w' ) as myfile_origin:
        json.dump({'vs': origin_hull.points[ origin_hull.vertices ].tolist(),'faces': origin_hull.points[ origin_hull.simplices ].tolist()}, myfile_origin, indent = 4 )




    end_time=time.clock()

    print ('time: ', end_time-start_time)




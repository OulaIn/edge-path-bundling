import numpy as np
import math
import pandas as pd
import typing
from typing import List
from tqdm import tqdm
import geopandas as gpd
import descartes
import matplotlib.pyplot as plt
import heapq

import bezier as bz
import airports
import migrations
import control_points
from model import Edge, Node
def toSphere(v):
        phi = v[0] # longitude
        theta = (np.pi/2) - v[1] # latitude
        x = np.sin(theta) * np.cos(phi)
        y = np.sin(theta) * np.sin(phi)
        z = np.cos(theta)
        return np.array([x,y,z])

def toPlane(v):
    r = np.linalg.norm(v)
    r2D = np.sqrt(np.square(v[0]) + np.square(v[1]))
    theta = np.arccos(v[2]/r)
    lat = (np.pi/2)-theta
    lon = np.sign(v[1]) * np.arccos(v[0]/r2D)
    return(np.array([lon,lat]))

def rotate(vector, axis, theta):
    """
    Return the rotation matrix associated with counterclockwise rotation about
    the given axis by theta radians.
    """
    axis = np.asarray(axis)
    axis = axis / math.sqrt(np.dot(axis, axis))
    a = math.cos(theta / 2.0)
    b, c, d = -axis * math.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    mat = np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])
    return (np.dot(mat, vector))


def evalBezierSpherical(controlPoints, t):
#arguments:  list of 2D-np.arrrays, int
    #Check if we have enough control points
    if len(controlPoints) < 2:
        retVal = np.array(0.0, 0.0)
        return retVal
    if (t <0 or t>1):
        retVal = np.array(0.0, 0.0)
        return retVal
    if (t==0):
        return controlPoints[0]
    if (t==1):
        return controlPoints[-1]

    #Calculate the intermediate points
    points3D = []
    for point in controlPoints:
        points3D.append(toSphere(np.radians(point)))
    while (len(points3D) > 1):
        intermediatePoints = []
        for i in range(len(points3D)-1):
            unit1 = points3D[i] / np.linalg.norm(points3D[i])
            unit2 = points3D[i+1] / np.linalg.norm(points3D[i+1])
            cosAlpha = np.dot(unit1,unit2)
            alpha = np.arccos(cosAlpha)
            axis = np.array([0,0,1])
            if alpha > 179.9:
                axis = np.cross(unit1, np.array([0,0,1]))
            else: 
                axis = np.cross(unit1, unit2)
            axis = axis/np.linalg.norm(axis)
            v = rotate(points3D[i], axis, t*alpha)
            intermediatePoints.append(v)
        points3D = intermediatePoints
    return np.degrees(toPlane(points3D[0]))


def createGeodesicPolygon(start, end, n=0, stepSize=1): # startPoint, endPoint, numberOfIntermediateSteps, stepsize
#arguments: 2d np.array , 2d np.array, int
#returns: 2d np.array
    if((start==end).all()):
        return start
    
    # calculate resolution
    numOfSteps = n
    if(n<=0):
        delta = np.abs(end-start)
        if delta[0] > 180: delta[0] = delta[0]-180
        numOfSteps = np.ceil(np.linalg.norm(delta) / np.abs(stepSize)).astype(int)

    #calculate Samples
    a = toSphere(np.radians(start))
    b = toSphere(np.radians(end))
    unit1 = a / np.linalg.norm(a)
    unit2 = b / np.linalg.norm(b)
    cosAlpha = np.dot(unit1,unit2)
    alpha = np.arccos(cosAlpha)
    axis = np.array([0,0,1])
    if alpha > 179.9:
        axis = np.cross(unit1, np.array([0,0,1]))
        axis = axis/axis(np.linalg.norm(axis))
    else: 
        axis = np.cross(unit1, unit2)
        axis = axis/np.linalg.norm(axis)
    samplesOnSphere = []

    for i in range(numOfSteps):
        v = rotate(a, axis, i*alpha/numOfSteps)
        samplesOnSphere.append(v)
    samplesOnSphere.append(b)
    samplesOnMap = []
    for sample3D in samplesOnSphere:
        samplesOnMap.append(np.degrees(toPlane(sample3D)))
    return samplesOnMap
#end of function


def createSphericalBezierPolygon(controlPoints, n = 0, stepSize=1): #n = number of points to approximate curve
#arguments: list of 2d-np.arrays , int, float
#returns: list of 2d np.arrays (points) on the bezier curve w.r.t spherical geometry
    if n==1:
        return [controlPoints[0],controlPoints[-1]]
    points = []
    
    # calculate resolution
    numOfSteps = n
    if(n<=0):
        length=0 # approximates curve length
        for i in range(len(controlPoints)-1):
            delta = controlPoints[i+1] - controlPoints[i]
            if delta[0] > 180: delta[0] = delta[0]-180
            length =  length + np.linalg.norm(delta)
        numOfSteps = np.ceil(length / np.abs(stepSize)).astype(int)

    # create sample points
    for i in range(numOfSteps):
        points.append(evalBezierSpherical(controlPoints, i/numOfSteps))
    points.append(controlPoints[-1])
    return points
#end of function


def plotSpherical(controlPointLists, nodes, edges, n=-1, stepSize = 1):
    # create and plot bezier curves
    for controlPoints in tqdm(controlPointLists, desc="Drawing3D: "):
        polygon = createSphericalBezierPolygon(controlPoints, n, stepSize)  # returns list of 2d vectors
        
        #split polygon into sections when it crosses 180deg boundary
        splitIndices=[]
        skip=False
        for i in range(len(polygon)-1):
            a=polygon[i]
            d=polygon[i+1]
            if np.sign(a[0]) != np.sign(d[0]) and np.abs(a[0]) > 170 and np.abs(d[0])> 170 and not skip:
                #create intermediate points close to border
                b = a
                b[0] = np.sign(a[0])*179.9
                b[1] = 0.5 * (a[1]+d[1])
                c=d
                c[0] = np.sign(d[0])*179.9
                c[1] = b[1]
                polygon.insert(i+1, b)
                polygon.insert(i+2, c)
                splitIndices.append(i+2)
                skip = True
            else: 
                skip = False   
        segments = np.split(polygon, splitIndices) 

        for segment in segments:
            x = [arr[0] for arr in segment.tolist()]
            y = [arr[1] for arr in segment.tolist()]
            plt.plot(x, y, color='red', linewidth=0.1, alpha=1)

    # draw lines without detour or with detour that was too long
    for edge in edges:
        if edge.skip:
            continue
        s = nodes[edge.source]
        d = nodes[edge.destination]
        start = np.array([s.longitude, s.latitude])
        end = np.array([d.longitude, d.latitude])
        polygon = createGeodesicPolygon(start, end, n, stepSize)

        #split polygon into sections when it corosse 180deg boundary
        splitIndices=[]
        skip=False
        for i in range(len(polygon)-1):
            a=polygon[i]
            d=polygon[i+1]
            if np.sign(a[0]) != np.sign(d[0]) and np.abs(a[0]) > 170 and np.abs(d[0])> 170 and not skip:
                #create intermediate points close to border
                b = a
                b[0] = np.sign(a[0])*179.9
                b[1] = 0.5 * (a[1]+d[1])
                c=d
                c[0] = np.sign(d[0])*179.9
                c[1] = b[1]
                polygon.insert(i+1, b)
                polygon.insert(i+2, c)
                splitIndices.append(i+2)
                skip = True
            else: 
                skip = False   
        segments = np.split(polygon, splitIndices) 


        for segment in segments:
            x = [arr[0] for arr in segment.tolist()]
            y = [arr[1] for arr in segment.tolist()]
            plt.plot(x, y, color='blue', linewidth=0.1,  alpha=1)

    for node in nodes.values():
        a = (node.longitude, node.latitude)
        c = plt.Circle(a, radius=0.1, color='green')
        #ax.add_patch(c)
    
    #draw boundaries
    boundaries=[[-180,-90],[-180, 90],[180,90],[180,-90],[-180,-90] ]
    x,y = zip(*boundaries)
    plt.plot(x, y, color='black', linewidth=0.1,  alpha=1)

    #plt.axis('scaled')
    ax = plt.gca()
    ax.set_aspect('equal', adjustable='box')
    plt.axis('On')
    plt.gcf().set_dpi(300)
    plt.tight_layout()
    plt.show()
#end of function
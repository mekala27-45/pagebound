"""Affine transforms with named spaces. Polygons stay polygons through rotation."""
from dataclasses import dataclass
from math import isfinite, floor, ceil
from .identity import ContractError, require_digest

def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ContractError("Coordinate must be a finite number")
    return float(value)

@dataclass(frozen=True)
class Affine:
    source: str
    target: str
    a: float = 1
    b: float = 0
    c: float = 0
    d: float = 1
    e: float = 0
    f: float = 0

    def __post_init__(self):
        for v in (self.a, self.b, self.c, self.d, self.e, self.f):
            number(v)
        if not self.source or not self.target or abs(self.a*self.d-self.b*self.c) < 1e-12:
            raise ContractError("Singular or unnamed transform")

    def point(self, point):
        x, y = map(number, point)
        return [self.a*x+self.c*y+self.e, self.b*x+self.d*y+self.f]

    def polygon(self, points):
        return [self.point(p) for p in points]

    def inverse(self):
        det = self.a*self.d-self.b*self.c
        return Affine(self.target, self.source, self.d/det, -self.b/det,
                      -self.c/det, self.a/det,
                      (self.c*self.f-self.d*self.e)/det,
                      (self.b*self.e-self.a*self.f)/det)

    def then(self, other):
        if self.target != other.source:
            raise ContractError("Transform space mismatch")
        a,b,c,d,e,f = self.a,self.b,self.c,self.d,self.e,self.f
        A,B,C,D,E,F = other.a,other.b,other.c,other.d,other.e,other.f
        return Affine(self.source,other.target,A*a+C*b,B*a+D*b,A*c+C*d,B*c+D*d,A*e+C*f+E,B*e+D*f+F)

def area(points):
    return abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(points,points[1:]+points[:1])))/2

def validate_polygon(points, width, height):
    w,h = number(width),number(height)
    if w <= 0 or h <= 0 or not isinstance(points,list) or not 3 <= len(points) <= 16:
        raise ContractError("Missing dimensions or polygon")
    pts = []
    for p in points:
        if not isinstance(p,(list,tuple)) or len(p) != 2:
            raise ContractError("Malformed vertex")
        x,y = map(number,p)
        if not (0 <= x <= w and 0 <= y <= h):
            raise ContractError("Polygon outside raster")
        pts.append([x,y])
    cross = []
    for i,p in enumerate(pts):
        q,r=pts[(i+1)%len(pts)],pts[(i+2)%len(pts)]
        cross.append((q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0]))
    if area(pts) <= 1e-8 or not (all(c>=0 for c in cross) or all(c<=0 for c in cross)):
        raise ContractError("Degenerate or unordered convex polygon")
    return pts

def box_polygon(box):
    if len(box)!=4:
        raise ContractError("Expected four bounds")
    x0,y0,x1,y1 = map(number,box)
    if x1<=x0 or y1<=y0:
        raise ContractError("Crop must have positive area")
    return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]

def pixel_crop(bounds, width, height, max_edge=512):
    pts=validate_polygon(box_polygon(bounds),1,1)
    x0,y0=pts[0];x1,y1=pts[2]
    box=[floor(x0*width),floor(y0*height),ceil(x1*width),ceil(y1*height)]
    if max(box[2]-box[0],box[3]-box[1])>max_edge:
        raise ContractError("Crop exceeds the pixel edge budget")
    return box

def bind_overlay(evidence, render):
    if require_digest(evidence["render_digest"]) != require_digest(render["sha256"]):
        raise ContractError("Overlay belongs to another rendering")
    return validate_polygon(evidence["polygon"],render["width"],render["height"])

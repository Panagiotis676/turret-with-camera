# python
import math

class CentroidTracker:
    def __init__(self, max_disappeared=30, max_distance=100):
        self.next_id = 0
        self.objects = {}          # id -> (x1,y1,x2,y2,cx,cy)
        self.disappeared = {}      # id -> frames disappeared
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, bbox):
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        self.objects[self.next_id] = (x1, y1, x2, y2, cx, cy)
        self.disappeared[self.next_id] = 0
        self.next_id += 1

    def deregister(self, object_id):
        if object_id in self.objects:
            del self.objects[object_id]
        if object_id in self.disappeared:
            del self.disappeared[object_id]

    def update(self, detections):
        # detections: list of (x1,y1,x2,y2)
        if len(detections) == 0:
            for oid in list(self.disappeared.keys()):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    self.deregister(oid)
            return self.objects

        input_centroids = []
        for (x1, y1, x2, y2) in detections:
            input_centroids.append(((x1 + x2) // 2, (y1 + y2) // 2))

        # Register all if no existing objects
        if len(self.objects) == 0:
            for bbox in detections:
                self.register(bbox)
            return self.objects

        object_ids = list(self.objects.keys())
        object_centroids = [ (v[4], v[5]) for v in self.objects.values() ]

        # build distance matrix (rows: existing objects, cols: detections)
        D = []
        for oc in object_centroids:
            row = []
            for ic in input_centroids:
                dx = oc[0] - ic[0]; dy = oc[1] - ic[1]
                row.append(math.hypot(dx, dy))
            D.append(row)

        # greedy matching by increasing row minimum distance
        rows_min = [(i, min(r)) for i, r in enumerate(D)]
        rows_min.sort(key=lambda x: x[1])

        assigned_rows = set()
        assigned_cols = set()

        for r, _ in rows_min:
            # find best column for this row
            row = D[r]
            c = min(range(len(row)), key=lambda j: row[j])
            if r in assigned_rows or c in assigned_cols:
                continue
            if row[c] > self.max_distance:
                continue
            object_id = object_ids[r]
            x1, y1, x2, y2 = detections[c]
            cx, cy = input_centroids[c]
            self.objects[object_id] = (x1, y1, x2, y2, cx, cy)
            self.disappeared[object_id] = 0
            assigned_rows.add(r)
            assigned_cols.add(c)

        # mark unassigned existing as disappeared
        for i, oid in enumerate(object_ids):
            if i not in assigned_rows:
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    self.deregister(oid)

        # register unassigned detections
        for i, bbox in enumerate(detections):
            if i not in assigned_cols:
                self.register(bbox)

        return self.objects

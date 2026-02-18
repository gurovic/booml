p = list(map(int, input().split()))
for i in range(len(p)):
    p[i]/=100
paths = [["000",[0, 1, 3]], ["001",[0, 1, 3]], ["010",[0, 1, 4]], ["011",[0, 1, 4]], ["100",[0, 2, 5]], ["101",[0, 2, 5]], ["110",[0, 2, 6]], ["111",[0, 2, 6]]]
otv = []
for s in paths:
    ver = 1.0
    for i in range(3):
        if s[0][i] == '0':
            ver *= p[s[1][i]]
        else:
            ver *= (1 - p[s[1][i]])
    otv.append([ver, s[0]])
otv.sort(key=lambda x: [x[0], x[1]])
for i in otv:
    print(i[1])
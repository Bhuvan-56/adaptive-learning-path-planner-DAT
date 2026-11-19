"""Builds data/demo/questions_maths.json (hand-written live-demo questions). Run: python data/demo/make_questions_maths.py"""
import json
import os
# (id/key, concept, stem, [correct, (wrong, why), ...], difficulty or None)
D = [
 ("item_003","ARITH","1/2 + 1/4 = ?",["3/4",("2/6","Added the tops and the bottoms; fractions need a common denominator first."),("1/6","Multiplied instead of adding."),("2/4","Added only the numerators and kept one denominator.")]),
 ("item_001","ARITH","Simplify 6/8.",["3/4",("3/8","Simplified only the numerator."),("2/3","Subtracted the same number from top and bottom instead of dividing."),("8/6","Turned the fraction upside down.")]),
 ("item_008","ARITH","Boys and girls in a class are in the ratio 2 : 3. There are 10 boys. How many girls?",["15",("11","Added 1 to match the 2 → 3 step instead of scaling."),("about 6.7","Applied the ratio the wrong way round."),("25","Gave the class total, not the girls.")]),
 ("item_005","ARITH","What is 3/5 of 20?",["12",("4","Found 1/5 and stopped."),("15","Divided by 4 instead of 5."),("100/3","Divided by 3/5 instead of multiplying.")]),
 ("item_004","ARITH","2/3 × 3/4 = ?",["1/2",("5/7","Added tops and bottoms instead of multiplying."),("8/9","Flipped the second fraction (that is the rule for division)."),("6/7","Multiplied the tops but added the bottoms.")]),
 ("item_006","ARITH","3/4 ÷ 3/8 = ?",["2",("9/32","Multiplied instead of dividing."),("1/2","Flipped the first fraction instead of the second."),("1","Divided the numerators (3 ÷ 3) and ignored the denominators.")]),
 ("item_002","ARITH","5/6 − 3/4 = ?",["1/12",("2/2","Subtracted tops and bottoms separately."),("2/12","Converted 3/4 to 8/12; it is 9/12."),("1/3","Treated 3/4 as 3/6 and subtracted.")]),
 ("item_007","ARITH","A recipe uses flour and sugar in the ratio 5 : 2. There are 350 g in total. How much sugar?",["100 g",("140 g","Took 2/5 of the total; the parts are 2 out of 7."),("70 g","Took 1/5 of the total."),("250 g","Found the flour, not the sugar.")]),
 ("item_009","VARS","If x = 3, what is 2x + 1?",["7",("24","Read 2x as the number 23."),("6","Forgot to add 1."),("8","Calculated 2(x + 1).")]),
 ("item_011","VARS","Simplify 3a + 2a.",["5a",("6a","Multiplied the coefficients."),("5a²","Added the powers as well."),("32a","Wrote the coefficients side by side.")]),
 ("item_016","VARS","Expand 2(x + 4).",["2x + 8",("2x + 4","Multiplied only the first term."),("x + 8","Multiplied only the second term."),("2x + 6","Added 2 instead of multiplying.")]),
 ("item_013","VARS","Simplify 4x + 3 − x + 5.",["3x + 8",("4x + 8","Ignored the − x."),("5x + 8","Added x instead of subtracting it."),("3x + 2","Subtracted 3 from 5 instead of adding.")]),
 ("item_012","VARS","If a = −2, what is a² + 3a?",["−2",("−10","Took a² as −4; (−2)² = 4."),("10","Took 3a as +6."),("2","Got the sign of the answer wrong.")]),
 ("item_010","VARS","Which is equal to 3(2x − 1) − 2x?",["4x − 3",("4x − 1","Multiplied only the first term in the bracket."),("8x − 3","Added the 2x instead of subtracting it."),("4x + 3","Lost the minus sign of −3.")]),
 ("item_014","VARS","Factorise 6x + 9.",["3(2x + 3)",("3(2x + 9)","Took the factor out of the first term only."),("6(x + 9)","Took 6 out of 9, which it does not divide."),("15x","Added unlike terms.")]),
 ("item_015","VARS","Write an expression for '5 less than twice a number n'.",["2n − 5",("5 − 2n","Reversed the order: 'less than' subtracts 5 from 2n."),("2(n − 5)","Subtracted before doubling."),("2n + 5","Read 'less than' as 'more than'.")]),
 ("item_019","LIN","Solve x + 7 = 12.",["x = 5",("x = 19","Added 7 instead of subtracting it."),("x = 12/7","Divided instead of subtracting."),("x = −5","Sign error when moving 7.")]),
 ("item_017","LIN","Solve 3x = 18.",["x = 6",("x = 15","Subtracted 3 instead of dividing."),("x = 54","Multiplied instead of dividing."),("x = 21","Added 3.")]),
 ("item_022","LIN","Solve 2x + 5 = 17.",["x = 6",("x = 11","Added 5 instead of subtracting it."),("x = 8.5","Divided 17 by 2 before removing the 5."),("x = 12","Forgot to divide by 2.")]),
 ("item_024","LIN","Solve 5x − 3 = 2x + 9.",["x = 4",("x = 12/7","Added 2x to both sides instead of subtracting it."),("x = 2","Combined −3 and 9 as 6 instead of 12."),("x = 12","Forgot to divide by 3.")]),
 ("item_023","LIN","Solve x/4 + 1 = 3.",["x = 8",("x = 1/2","Divided 2 by 4 instead of multiplying."),("x = 16","Added 1 instead of subtracting it."),("x = 2","Stopped before multiplying by 4.")]),
 ("item_021","LIN","Solve 3(x − 2) = 12.",["x = 6",("x = 14/3","Multiplied only the x by 3."),("x = 2","Subtracted 2 instead of adding it."),("x = 4","Stopped at x − 2 = 4.")]),
 ("item_020","LIN","Solve 2(x + 3) = 4x − 2.",["x = 4",("x = 5/2","Multiplied only the x in the bracket."),("x = −4","Sign error when moving terms."),("x = 8","Stopped at 2x = 8 without dividing by 2.")]),
 ("item_018","LIN","A taxi charges ₹50 plus ₹12 per km. A ride cost ₹170. How many km?",["10 km",("about 14.2 km","Forgot to remove the fixed ₹50 first."),("about 18.3 km","Added the ₹50 instead of subtracting it."),("120 km","Forgot to divide by ₹12 per km.")]),
]
P = [
 ("ARITH",0.05,"1/3 + 1/3 = ?",["2/3",("2/6","Added the tops and the bottoms."),("1/9","Multiplied instead of adding."),("1/3","Kept one fraction only.")]),
 ("ARITH",0.15,"Which fraction equals 0.4?",["2/5",("4/100","0.4 is four tenths, not four hundredths."),("1/4","Matched the digit 4 to a quarter."),("4/5","0.4 is 4/10, which simplifies to 2/5.")]),
 ("ARITH",0.25,"What is 3/4 of 36?",["27",("9","Found 1/4 and stopped."),("48","Divided by 3 and multiplied by 4."),("12","Divided by 3.")]),
 ("ARITH",0.35,"Share ₹60 in the ratio 1 : 2. What is the larger share?",["₹40",("₹30","Split equally."),("₹20","Gave the smaller share."),("₹120","Multiplied by 2 instead of sharing.")]),
 ("VARS",0.10,"If y = 4, what is 3y − 2?",["10",("32","Read 3y as the number 34."),("12","Forgot to subtract 2."),("6","Calculated 3(y − 2).")]),
 ("VARS",0.20,"Simplify 5b − 2b + b.",["4b",("2b","Subtracted the + b as well."),("3b","Dropped the + b."),("8b","Added every term.")]),
 ("VARS",0.30,"Expand 3(2x − 5).",["6x − 15",("6x − 5","Multiplied only the first term."),("5x − 15","Added 3 to 2x."),("6x + 15","Lost the minus sign.")]),
 ("VARS",0.40,"Simplify 2(x + 3) + 3(x − 1).",["5x + 3",("5x + 5","Multiplied only the x in 3(x − 1)."),("5x + 9","Took −3 as +3."),("5x − 3","Dropped the +6.")]),
 ("LIN",0.20,"Solve x − 4 = 9.",["x = 13",("x = 5","Subtracted 4 again instead of adding it."),("x = −13","Sign error."),("x = 36","Multiplied.")]),
 ("LIN",0.30,"Solve 4x + 2 = 22.",["x = 5",("x = 6","Added 2 instead of subtracting it."),("x = 20","Forgot to divide by 4."),("x = 5.5","Divided before removing the 2.")]),
 ("LIN",0.40,"Solve 7x − 4 = 3x + 8.",["x = 3",("x = 1.2","Added 3x instead of subtracting it."),("x = 1","Took −4 and 8 as 4."),("x = −3","Sign error when moving terms.")]),
 ("LIN",0.50,"Solve (2x − 1)/3 = 5.",["x = 8",("x = 3","Forgot to multiply by 3 first."),("x = 7","Subtracted 1 instead of adding it."),("x = 16","Stopped at 2x = 16 without dividing by 2.")]),
 ("FUNC",0.25,"f(x) = 2x + 3. What is f(4)?",["11",("24","Multiplied 2 × 4 × 3."),("9","Added 2 + 4 + 3."),("8","Forgot the + 3.")]),
 ("FUNC",0.35,"f(x) = x² − 1. What is f(−3)?",["8",("−10","Took (−3)² as −9."),("10","Added 1 instead of subtracting."),("−8","Sign error at the end.")]),
 ("FUNC",0.45,"Which of these is NOT a function?",["{(1, 2), (1, 3), (2, 4)}",("{(1, 2), (2, 3), (3, 4)}","Each input has exactly one output, so this is a function."),("{(1, 5), (2, 5), (3, 5)}","Repeated outputs are allowed; repeated inputs with different outputs are not."),("y = 3x","Every x gives exactly one y.")]),
 ("FUNC",0.55,"f(x) = 3x − 2 and f(a) = 10. What is a?",["4",("28","Calculated f(10) instead of solving f(a) = 10."),("8/3","Subtracted 2 instead of adding it."),("12","Forgot to divide by 3.")]),
 ("LINF",0.30,"What is the slope of y = 4x − 7?",["4",("−7","That is the y-intercept."),("7","Took the intercept and dropped its sign."),("−4","Sign error.")]),
 ("LINF",0.40,"Which line passes through (0, 2) with slope 3?",["y = 3x + 2",("y = 2x + 3","Swapped the slope and the intercept."),("y = 3x − 2","Wrong sign on the intercept."),("y = x + 5","Added slope and intercept.")]),
 ("LINF",0.50,"What is the slope of the line through (1, 2) and (3, 8)?",["3",("1/3","Divided run by rise."),("6","Used the rise only."),("2","Used the run only.")]),
 ("LINF",0.60,"Which line passes through (2, 5) and (4, 9)?",["y = 2x + 1",("y = 2x + 5","Used the y-value at x = 2 as the intercept."),("y = x/2 + 4","Inverted the slope."),("y = 4x − 3","Took slope as 9 − 5.")]),
 # Added for the 16-concept simulations (site/sim.html): every concept of the maths curriculum.
 ("EXPO",0.15,"2³ × 2² = ?",["2⁵",("2⁶","Multiplied the powers; when multiplying, powers add."),("4⁵","Multiplied the bases as well."),("2¹","Subtracted the powers.")]),
 ("EXPO",0.25,"√49 + √16 = ?",["11",("√65","Added under one root; square roots do not add like that."),("65","Added the squares instead of the roots."),("3","Subtracted the roots.")]),
 ("EXPO",0.35,"(x⁴)³ = ?",["x¹²",("x⁷","Added the powers; a power of a power multiplies them."),("x⁶⁴","Raised 4 to the power 3."),("3x⁴","Multiplied by 3 instead of raising to the power 3.")]),
 ("INEQ",0.25,"Solve x + 3 > 7.",["x > 4",("x > 10","Added 3 instead of subtracting it."),("x < 4","Flipped the sign without a reason."),("x = 4","Solved as an equation.")]),
 ("INEQ",0.35,"Solve 2x − 1 ≤ 9.",["x ≤ 5",("x ≤ 4","Subtracted 1 instead of adding it."),("x ≥ 5","Flipped the sign; only dividing by a negative flips it."),("x ≤ 10","Forgot to divide by 2.")]),
 ("INEQ",0.45,"Solve −3x < 12.",["x > −4",("x < −4","Did not flip the sign when dividing by a negative."),("x > 4","Lost the minus sign."),("x < 4","Lost the minus sign and did not flip.")]),
 ("SYS",0.35,"x + y = 10 and x − y = 2. What is x?",["6",("4","That is y."),("8","Subtracted the equations instead of adding them."),("12","Added the equations but did not divide by 2.")]),
 ("SYS",0.45,"2x + y = 7 and x + y = 4. Which pair solves both?",["(3, 1)",("(1, 3)","Swapped x and y."),("(2, 3)","Satisfies only the first equation."),("(4, 0)","Satisfies only the second equation.")]),
 ("SYS",0.55,"Where do y = 2x + 1 and y = x + 4 meet?",["(3, 7)",("(7, 3)","Swapped x and y."),("(3, 4)","Found x but took y from the constant."),("(−3, −5)","Sign error when solving 2x + 1 = x + 4.")]),
 ("QUAD",0.40,"Solve x² = 25.",["x = 5 or x = −5",("x = 5","Forgot the negative root."),("x = 12.5","Halved instead of taking the square root."),("x = ±25","Did not take the square root.")]),
 ("QUAD",0.50,"Solve x² − 5x + 6 = 0.",["x = 2 or x = 3",("x = −2 or x = −3","Sign error: (x − 2)(x − 3) gives x = 2, 3."),("x = 1 or x = 6","Factors of 6 that do not add up to 5."),("x = 6","Read the constant term as the answer.")]),
 ("QUAD",0.60,"Solve x² + 2x − 8 = 0.",["x = 2 or x = −4",("x = −2 or x = 4","Sign error in (x + 4)(x − 2)."),("x = 8 or x = −1","Factors of 8 that do not add up to 2."),("x = 2 or x = 4","Ignored the signs.")]),
 ("POLY",0.40,"Expand (x + 2)(x + 3).",["x² + 5x + 6",("x² + 6","Forgot the middle terms."),("x² + 6x + 5","Multiplied where it should add, and the reverse."),("2x + 5","Added the brackets.")]),
 ("POLY",0.50,"What is the degree of 4x³ − 2x⁵ + 7?",["5",("3","Took the first term's power; the degree is the highest power."),("4","Took the leading coefficient."),("8","Added the powers.")]),
 ("POLY",0.60,"(x³ − 8) ÷ (x − 2) = ?",["x² + 2x + 4",("x² − 4","Divided term by term."),("x² − 2x + 4","Sign error in the middle term."),("x² + 4","Dropped the middle term.")]),
 ("EXPF",0.45,"f(x) = 3ˣ. What is f(2)?",["9",("6","Multiplied 3 × 2."),("8","Calculated 2³."),("5","Added 3 + 2.")]),
 ("EXPF",0.55,"100 grows by 10% each year. What is it after 2 years?",["121",("120","Added 10% of the original twice; growth compounds."),("110","Applied one year only."),("200","Doubled.")]),
 ("EXPF",0.65,"Which of these is exponential decay?",["y = 5(0.8)ˣ",("y = 5(1.2)ˣ","A base above 1 is growth."),("y = 5 − 0.8x","That is linear."),("y = 0.8x²","That is quadratic.")]),
 ("LOG",0.50,"log₂ 8 = ?",["3",("4","Divided 8 by 2."),("16","Multiplied 8 by 2."),("6","Subtracted 2 from 8.")]),
 ("LOG",0.60,"log₁₀ 1000 = ?",["3",("100","Divided 1000 by 10."),("30","Multiplied the number of zeros by 10."),("0.001","Took the reciprocal.")]),
 ("LOG",0.70,"log(ab) = ?",["log a + log b",("log a × log b","The log of a product is a sum, not a product."),("log a − log b","That is log(a / b)."),("a · log b","That is log(bᵃ).")]),
 ("TRIG",0.45,"In a right-angled triangle, sin θ = ?",["opposite / hypotenuse",("adjacent / hypotenuse","That is cos θ."),("opposite / adjacent","That is tan θ."),("hypotenuse / opposite","Inverted the ratio.")]),
 ("TRIG",0.55,"sin 30° = ?",["1/2",("√3/2","That is cos 30°."),("1","That is sin 90°."),("30","Confused the angle with its sine.")]),
 ("TRIG",0.65,"tan θ = 1 and 0° < θ < 90°. What is θ?",["45°",("1°","Took the ratio as the angle."),("90°","tan 90° is undefined."),("60°","tan 60° = √3.")]),
 ("LIM",0.60,"lim (x → 3) of (2x + 1) = ?",["7",("6","Forgot the + 1."),("∞","A polynomial has a finite limit at a finite point."),("3","Gave the value x approaches.")]),
 ("LIM",0.70,"lim (x → 2) of (x² − 4)/(x − 2) = ?",["4",("No limit, because 0/0","0/0 means factorise first: (x + 2)(x − 2)/(x − 2)."),("0","Substituted only in the numerator."),("2","Gave the value x approaches.")]),
 ("LIM",0.80,"lim (x → ∞) of (3x + 1)/(x + 5) = ?",["3",("1/5","Used the constant terms."),("0","Assumed every fraction tends to 0."),("∞","The top and bottom grow at the same rate.")]),
 ("DER",0.65,"d/dx (x³) = ?",["3x²",("x²","Lowered the power but forgot to multiply by 3."),("3x³","Multiplied by 3 but kept the power."),("x⁴/4","Integrated instead of differentiating.")]),
 ("DER",0.75,"d/dx (5x² + 3x) = ?",["10x + 3",("10x","Forgot the derivative of 3x."),("5x + 3","Forgot to multiply by the power 2."),("10x² + 3","Kept the power.")]),
 ("DER",0.85,"What is the slope of y = x² at x = 3?",["6",("9","Gave the y-value, not the slope."),("3","Gave the x-value."),("2","Used the derivative's coefficient only.")]),
 ("INT",0.75,"∫ 2x dx = ?",["x² + C",("2 + C","Differentiated instead of integrating."),("2x² + C","Raised the power but did not divide by it."),("x + C","Dropped the power.")]),
 ("INT",0.85,"∫ from 0 to 2 of 3x² dx = ?",["8",("12","Evaluated 3x² at 2 instead of integrating."),("6","Evaluated 3x at 2."),("24","Forgot to divide by the new power.")]),
 ("INT",0.95,"∫ (1/x) dx, for x > 0 = ?",["ln x + C",("x⁰/0 + C","The power rule fails for x⁻¹."),("−1/x² + C","Differentiated instead of integrating."),("1/x² + C","Guessed a power.")]),
]
def make(i, stem, opts):
    correct, wrongs = opts[0], opts[1:]
    pos = i % 4
    options = [w[0] for w in wrongs]
    options.insert(pos, correct)
    why = {}
    for w in wrongs:
        why[str(options.index(w[0]))] = w[1]
    return {"stem": stem, "options": options, "answer": pos, "misconceptions": why}
out = {"description": "Hand-written demo questions for the live demo (site/live.html). NOT from any dataset. Diagnostic keys are the item ids of data/processed/item_bank_synthetic.csv mapped to concepts by data/processed/q_matrix_maths.csv; question difficulty was written to follow each item's IRT b (easier for lower b). Practice difficulty is on the engine's 0-1 exercise scale (src/planning/difficulty.py). Each wrong option names the misconception it indicates.",
       "diagnostic": {}, "practice": {}}
for i,(key,c,stem,opts) in enumerate(D):
    out["diagnostic"][key] = {"concept": c, **make(i, stem, opts)}
for i,(c,d,stem,opts) in enumerate(P):
    lst = out["practice"].setdefault(c, [])
    q = {"id": f"p_{c.lower()}_{len(lst)+1}", "concept": c, "difficulty": d, **make(i+1, stem, opts)}
    lst.append(q)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions_maths.json"),"w",encoding="utf-8"), indent=1, ensure_ascii=False)
# sanity
for k,q in out["diagnostic"].items(): assert len(set(q["options"]))==4, k
for c,l in out["practice"].items():
    for q in l: assert len(set(q["options"]))==4, q["id"]
print(len(out["diagnostic"]), {c:len(l) for c,l in out["practice"].items()})
from collections import Counter; print(Counter(q["answer"] for q in out["diagnostic"].values()))

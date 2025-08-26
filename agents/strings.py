examples = """

# Example of correct and incorrect annotation

In the first example, a single annotation links the indicated span to a pre-coordinated SNOMED
concept that subsumes the concepts of "fracture" and "rib". This is preferred to the second example
in which two separate annotations have been created.

Correct:
`Examination revealed a [hairline fracture in the first vertebrosternal rib (L)](760851 | Fracture of left rib)`

Incorrect:
`Examination revealed a [hairline fracture](75053 | Fracture of bone) in the [first vertebrosternal rib (L)](37110130 | Bone structure of left rib)`

# A realistic example

The example below shows the typical density of annotations seen in a passage for free-text.

`The patient was also given [glucorticoids](4178376 | Glucocorticoids and synthetic analogues) in setting of potential [adrenal insufficiency](40624051 | Adrenal cortical hypofunction) linked to chronic [predisone](4180039 | Administration of steroid) use for [PMR](255348 | Polymyalgia rheumatica). [Pressors](4235399 | Hypotensive therapy) were weaned off.`


# High concept entropy

These examples show three, lexically diverse spans that have been linked to the same clinical concept. This is an example of a concept with "high concept entropy".

`There is [calcification of the aortic knob](4108164 | Aortic valve calcification), unchanged with a slightly tortuous aorta.`

`[Aortic valve calcifications](4108164 | Aortic valve calcification)) are suspected on the lateral view.`

`No overlying sternal fx or aortic injury. dense [aortic calcs](4108164 | Aortic valve calcification).`

# High annotation entropy

The span "liver" is linked to three different clinical concepts, depending on the context in which it 
appears. If a high proportion of the spans linked to a concept have this property, the concept is said to
have "high annotation entropy". (Note that in the first example, the correct span to annotate is "liver", 
not "cancer - lung and liver" because a second annotation linking "lung" to concept (258369, Primary malignant 
neoplasm of lung) is required, and our guidelines prohibit overlapping annotations.)

`Family History of cancer - lung and [liver](4246127 | Malignant neoplasm of liver).`

`Stable [liver](195392 | Laceration of liver) and renal lacerations.`

`The [liver](4115573 | Liver normal), gallbladder, pancreas, adrenal glands, kidneys and ureters are unremarkable.`

"""
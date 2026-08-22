## ORTHO SENSE AI
# AI-Powered Podiatric Pressure Mapping and Diabetic Orthotic Printing Engine

## About the Project

"We are working on a system that analyzes foot pressure and uses the results to help design personalised orhtotics."

## Problem Statement

Patients with diabetic neuropathy suffer from loss of feeling in their feet, making them unaware of high-friction pressure points caused by standard footwear. Left unmanaged, these localized pressure points lead to diabetic foot ulcers (DFUs), severe infections, and eventual lower-limb amputations. Traditional custom orthotic insoles rely on static plaster casts that fail to capture dynamic foot pressure distribution while walking, resulting in insoles that do not effectively offload high-risk pressure zones.

## Objectives

To build a personalized podiatric care platform that prevents diabetic foot ulcers. The system will analyze dynamic walking pressure data from smart insoles, generate 3D volumetric models of the patient's foot mechanics, and automatically design custom, dual-density 3D-printed orthotic insoles that offload tissue pressure away from high-risk ulcer zones.


## How It Works

Dynamic Gait & Gait-Pressure Analyzer (Time-Series Spatial-Temporal Graph Networks): Processes sensor data from flexible pressure-matrix insoles while the patient walks. Maps peak plantar pressure points, stance duration, pronation angles, and shear stress across the heel, midfoot, and metatarsals.

Tissue Strain & Deformation Modeler (Biomechanical Finite Element Analysis & PINNs): Simulates how internal soft tissue layers deform under localized plantar pressure, identifying hidden micro-vascular ischemia risks before surface skin breakdown occurs.

Automated Offloading Orthotic Generator (Generative Parametric CAD Engine): Automatically alters 3D orthotic insole geometry—creating customized recessed zones and applying softer, energy-absorbing lattice structures directly beneath high-risk plantar pressure areas.


## Technologies Used

- **Programming:** Python
- **Data Processing:** NumPy, Pandas
- **Computer Vision:** OpenCV
- **Deep Learning:** PyTorch
- **Backend:** FastAPI
- **Frontend:** React
- **Database:** SQLite
- **3D Processing:** Open3D, Trimesh
- **3D Model Format:** STL
- **Development:** Google Colab, VS Code
- **Version Control:** Git, GitHub


## Project Structure

```text
Ortho_Sense-AI/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
├── notebooks/
├── preprocessing/
├── models/
├── orthotic_engine/
└── outputs/



## Current Progress

- [Done] Created the project repository
- [Working] Collect and analyze the
  dataset
- [ ] Preprocess pressure-map data
- [ ] Train the ML model
- [ ] Generate orthotic recommendations
- [ ] Connect the model with the 
  application

## Future Scope

80% Reduction in Diabetic Foot Ulcer Incidence: Prevent skin breakdown and costly hospitalizations by offloading critical plantar pressure points dynamically.

Precision Dynamic Orthotic Fitting: Replace static, uncomfortable plaster casts with functional insoles engineered directly from real-world walking mechanics.

Lower Amputation Rates & Healthcare Savings: Save healthcare systems thousands of dollars per diabetic patient by preventing severe lower-limb ulcer complications.

## Team Members
**Kritika Saxena** and
**Mradul Khandelwal**
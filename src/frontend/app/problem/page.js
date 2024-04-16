"use client";

import styles from "./page.module.css";
import { useState } from "react";

export default function Content() {
  async function send() {
    const formData = new FormData();
    
    formData.append("problemType", JSON.stringify(problemType));
    formData.append("objective", JSON.stringify({"formula": formula, "sense": sense}));
    formData.append("variables", JSON.stringify(variables.filter((v) => (v.value != "")).map((v) => (v.value))));
    formData.append("constraints", JSON.stringify(constraints.filter((c) => (c.value != "")).map((c) => (c.value))));
    
    Array.from(files).forEach((file) => {formData.append("file", file)});

    const response = await fetch("http://127.0.0.1:8080/api/home", {
      method: "POST",
      body: formData
    });
    const data = await response.json();
  }

  const problemTypes = [
    { value: "portfolio_optimization", display: "Portfolio Optimization" },
    { value: "mathematical_optimization", display: "Mathematical Optimization" },
    { value: "location_analysis", display: "Location Analysis" },
  ];
  const [problemType, setProblemType] = useState("portfolio_optimization");

  const senses = [
    { value: "minimize", display: "Minimize" },
    { value: "maximize", display: "Maximize" }
  ];
  const [sense, setSense] = useState("");
  const [formula, setFormula] = useState("");
  
  const [variables, setVariables] = useState([{value: ""}]);
  const [constraints, setConstraints] = useState([{value: ""}]);
  const [files, setFiles] = useState([]);

  return (
    <main className={styles.main}>

      <div className={styles.form}>
        <div>
          <h1>Problem type</h1>
          <div className={styles.problems}>
            {problemTypes.map((item) => (
              <div className={problemType === item.value ? styles.probsel : styles.prob} onClick={() => {setProblemType(item.value)}}>
                <p>{item.display}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h1>File(s)</h1>
          <input type="file" name="file" multiple onChange={(e) => {setFiles(e.target.files)}}/>
        </div>
  
        <div>
          <h1>Variables</h1>
          {variables.map((variable, index) => (
            <div>
              <Variable variable={variable} />
              <button onClick={() => {setVariables(variables.toSpliced(index, 1))}}>X</button>
            </div>
          ))}
          <div>
          <button onClick={() => {setVariables([...variables, {value: ""}])}}>add variable</button>
          </div>
        </div>

        <div>
          <h1>Objective</h1>
          <select name="sense" className={styles.select} onChange={(e) => (setSense(e.target.value))}>
            <option value="">Select type</option>
            {senses.map((o) => (<option value={o.value}>{o.display}</option>))}
          </select>
          <input type="text" name="formula" onChange={(e) => {setFormula(e.target.value)}} />
        </div>

        <div>
          <h1>Constraints</h1>
          {constraints.map((con, index) => (
            <div>
              <Constraint con={con} />
              <button onClick={() => {setConstraints(constraints.toSpliced(index, 1))}}>X</button>
            </div>
          ))}
          <button onClick={() => {setConstraints([...constraints, {value: ""}])}}>add constraint</button>
        </div>
        
        <div>
          <button onClick={send}>Run problem</button>
        </div>
      </div>
    </main>
  );
}

function Variable({ variable }) {
  const [value, setValue] = useState();
  return (
      <div className={styles.dynamiclist}>
        <input type="text" name="variable" value={variable.value} onChange={(e) => {setValue(e.target.value); variable.value = e.target.value}} />
      </div>
  );
}

function Constraint({ con }) {
  const [constraint, setConstraint] = useState();
  return (
    <div className={styles.dynamiclist}>
      <input type="text" name="constraint" value={con.value} onChange={(e) => {setConstraint(e.target.value); con.value = e.target.value}} />
    </div>
  );
}

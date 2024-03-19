"use client";

import styles from "./page.module.css";
import { useState } from "react";

export default function Content() {
  async function onSubmit(event) {
    event.preventDefault();
 
    const formData = new FormData(event.target);
    formData.append("problemType", problemType)
    console.log(formData);
    /*
    const response = await fetch("http://127.0.0.1:8080/api/home", {
      method: "POST",
      body: formData
    });
    const data = await response.json();
    */
  }

  async function send() {
    const formData = new FormData();
    formData.append("problemType", problemType);
    Object.keys(files).forEach((file) => {formData.append("file", files[file])});
    variables.forEach((variable) => {if (variable.value != "") {formData.append("variable", variable.value)}});
    constraints.forEach((constraint) => {if (constraint.lvar != "" && constraint.relation != "" && constraint.rvar != "") {formData.append("constraint", constraint.lvar.concat(constraint.relation, constraint.rvar))}});
    console.log(formData);
    /*
    const response = await fetch("http://127.0.0.1:8080/api/home", {
      method: "POST",
      body: formData
    });
    const data = await response.json();
    */
  }

  const problemTypes = [
    { value: "solver", display: "Solver" },
    { value: "optimizer", display: "Optimizer" },
    { value: "coverage", display: "Coverage" },
  ];
  const [problemType, setProblemType] = useState("solver");

  const objectives = [
    { value: "minimize", display: "Minimize" },
    { value: "maximize", display: "Maximize" }
  ];
  const [objective, setObjective] = useState()
  
  const [constraints, setConstraints] = useState([{lvar: "", relation: ">", rvar: ""}]);
  const [variables, setVariables] = useState([{value: ""}]); // leave object blank?
  const [files, setFiles] = useState([]);

  return (
    <main className={styles.main}>
      <div className={styles.problems}>
        <h2>Problem type:</h2>
        {problemTypes.map((item) => (
          <div className={problemType === item.value ? styles.probsel : styles.prob} onClick={() => {setProblemType(item.value)}}>
            <p>{item.display}</p>
          </div>
        ))}
      </div>

      <div className={styles.form}>
        <div>
          <h2>File(s)</h2>
          <input type="file" name="file" multiple className={styles.fileupload} onChange={(e) => {setFiles(e.target.files)}}/>
        </div>
  
        <div>
          <h2>variables</h2>
          {variables.map((variable, index) => (
            <div>
              <Variable variable={variable} />
              <button onClick={() => {setVariables(variables.toSpliced(index, 1))}}>remove</button>
            </div>
          ))}
          <div>
          <button onClick={() => {setVariables([...variables, {value: ""}])}}>add variable</button>
          </div>
        </div>

        <div>
          <h2>Objective</h2>
          <select name="objective" className={styles.select}>
            <option value="">Select type</option>
            {objectives.map((o) => (<option value={o.value}>{o.display}</option>))}
          </select>
        </div>

        <div>
          <h2>constraints</h2>
          {constraints.map((con, index) => (
            <div>
              <Constraint con={con} vars={variables} />
              <button onClick={() => {setConstraints(constraints.toSpliced(index, 1))}}>remove</button>
            </div>
          ))}
          <button onClick={() => {setConstraints([...constraints, {lvar: "", relation: ">", rvar: ""}])}}>add constraint</button>
        </div>
        
        <div>
          <button onClick={send}>log form contents to console</button>
        </div>
      </div>
    </main>
  );
}

function Constraint({ con }) {
  const relations = [
    ">",
    ">=",
    "<",
    "<=",
  ];
  const [rel, setRel] = useState(con.relation);
  const [lvar, setLvar] = useState(con.lvar);
  const [rvar, setRvar] = useState(con.rvar);
  return (
    <div className={styles.constraint}>
      <input name="lvar" value={con.lvar} onChange={(e) => {setLvar(e.target.value); con.lvar = e.target.value}} />
      <select name="relation" value={con.relation} onChange={(e) => {setRel(e.target.value); con.relation = e.target.value}}>
        {relations.map((relation) => (<option value={relation}>{relation}</option>))}
      </select>
      <input name="rvar" value={con.rvar} onChange={(e) => {setRvar(e.target.value); con.rvar = e.target.value}} />
    </div>
  );
}

function Variable({ variable }) {
  const [value, setValue] = useState();
  return (
      <div className={styles.variable}>
        <input name="variable" value={variable.value} onChange={(e) => {setValue(e.target.value); variable.value = e.target.value}} />
      </div>
  );
}

function Form({onSubmit}) {
  return (
    <form className={styles.form} onSubmit={onSubmit} enctype="multipart/form-data">
      <label className={styles.label} id='file'>
          <h1>File(s)</h1>
          <input type="file" name="file" multiple className={styles.fileupload} />
      </label>

      <label className={styles.label}>
          <h1>Variables</h1>
          <input type="text" name="variables" className={styles.input} />
      </label>

      <label className={styles.label}>
          <h1>Objective</h1>
          <select name="objective" className={styles.select}>
            <option value="">Select type</option>
            <option value="minimize">Minimize</option>
            <option value="maximize">Maximize</option>
          </select>
      </label>

      <label className={styles.label}>
          <h1>Constraints</h1>
          <input type="text" name="constraints" className={styles.input} />
      </label>

      <button type="submit" className={styles.button}>Submit</button>
    </form>
  );
}

"use client";

import styles from "./page.module.css";
import { use, useEffect, useState } from "react";

export default function Page() {

    //Create a form to submit the problem, use `useEffect` to submit the form
    const [problemType, setProblemType] = useState("solver");
    const [variables, setVariables] = useState([]);
    const [objective, setObjective] = useState("minimize");
    const [constraints, setConstraints] = useState([]);
    //TODO: File submission not working
    const [files, setFiles] = useState([]);
    const [submitted, setSubmitted] = useState(false);

    useEffect(() => {
        if (submitted) {
          //redirect to python server
            fetch("http://127.0.0.1:8080/api/home", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    problemType: problemType,
                    variables: variables,
                    objective: objective,
                    constraints: constraints,
                    files: files,
                }),
            })
            .then((response) => response.json())
            .then((data) => {
                setVariables(data);
            })
            .catch((error) => {
                console.error("Error:", error);
            });
        }
    }, [submitted]);

    return (
      <div className={styles.page}>
        <form onSubmit={(event) => {event.preventDefault(); setSubmitted(true);}}>
          <div>
            <label>
              Problem Type:
              <select value={problemType} onChange = {(event) => {setProblemType(event.target.value);}}>
                <option value="solver">Solver</option>
                <option value="optimizer">Optimizer</option>
                <option value="ect">...</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              File(s):
              <input type="file" onChange = {(event) => {setFiles(event.target.value);}} />
            </label>
          </div>
          <div>
            <label>
              Variables:
              <input type="text" value={variables[0]} onChange={(event) => {setVariables([event.target.value]);}} />
            </label>
          </div>
          <div>
            <label>
              Objective:
              <select value={objective} onChange = {(event) => {setObjective(event.target.value);}}>
                <option value="minimize">Minimize</option>
                <option value="maximize">Maximize</option>  
              </select>
            </label>
          </div>
          <div>
            <label>
              Constraints:
              <input type="text" value={constraints[0]} onChange={(event) => {setConstraints([event.target.value]);}} />
            </label>
          </div>
          <div>
            <button type="submit">Submit</button>
          </div>
        </form>
      </div>
    );
}      
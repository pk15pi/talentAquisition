import {useEffect,useState,type FormEvent} from 'react';
import api from '../../services/api';

type Job={id:string;job_code:string;title:string;location:string;status:string;priority:string};
type Client={id:string;company_name:string};

export default function Jobs(){
  const [items,setItems]=useState<Job[]>([]);
  const [clients,setClients]=useState<Client[]>([]);
  const [title,setTitle]=useState('');
  const [client,setClient]=useState('');
  const [jd,setJd]=useState('');
  const [min,setMin]=useState('');
  const [max,setMax]=useState('');
  const [location,setLocation]=useState('');
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');

  async function load(){
    const [j,c]=await Promise.all([api.get('/jobs/'),api.get('/clients/')]);
    setItems(j.data.results??j.data);
    setClients(c.data.results??c.data);
  }
  useEffect(()=>{load().catch(()=>setError('Unable to load jobs or clients.'));},[]);

  async function create(e:FormEvent){
    e.preventDefault();
    setError('');
    try{
      await api.post('/jobs/',{client,title,jd_text:jd,experience_min:min,experience_max:max,location,status:'OPEN',priority:'MEDIUM'});
      setTitle('');setJd('');setMin('');setMax('');setLocation('');
      load();
    }catch{
      setError('Could not create JD. Check that the client and experience range are valid.');
    }
  }

  async function match(id:string){
    setError('');
    setNotice('');
    try{
      const response=await api.post(`/jobs/${id}/match/`);
      const count=Number(response.data.candidates_processed??0);
      setNotice(`Matched ${count} active candidate${count===1?'':'s'}. Nobody was shortlisted or rejected automatically.`);
    }catch(err){
      const detail=(err as {response?:{data?:{detail?:string}}}).response?.data?.detail;
      setError(detail||'Matching could not be run.');
    }
  }

  return <>
    <div className="page-heading"><div><span className="eyebrow">RECRUITMENT</span><h1>Job descriptions</h1><p>Create requirements and track recruiter assignments.</p></div></div>
    {error&&<div className="error">{error}</div>}
    {notice&&<div className="match-panel"><div className="match-head"><h3>{notice}</h3></div></div>}
    <form className="create-form" onSubmit={create}><h3>Create a JD</h3><div className="form-grid"><select value={client} onChange={e=>setClient(e.target.value)} required><option value="">Select client</option>{clients.map(c=><option value={c.id} key={c.id}>{c.company_name}</option>)}</select><input placeholder="Job title" value={title} onChange={e=>setTitle(e.target.value)} required/><input placeholder="Minimum experience (years)" type="number" step="0.5" value={min} onChange={e=>setMin(e.target.value)} required/><input placeholder="Maximum experience (years)" type="number" step="0.5" value={max} onChange={e=>setMax(e.target.value)} required/><input placeholder="Location" value={location} onChange={e=>setLocation(e.target.value)}/></div><textarea placeholder="Paste job description" value={jd} onChange={e=>setJd(e.target.value)} required/><button className="primary">Create JD</button></form>
    <div className="table-wrap"><table><thead><tr><th>JD</th><th>Title</th><th>Location</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead><tbody>{items.map(j=><tr key={j.id}><td>{j.job_code}</td><td><b>{j.title}</b></td><td>{j.location||'—'}</td><td>{j.priority}</td><td><span className="tag">{j.status}</span></td><td><button className="small-action" type="button" onClick={()=>match(j.id)}>Find candidates</button></td></tr>)}{!items.length&&<tr><td colSpan={6} className="empty">No JDs found.</td></tr>}</tbody></table></div>
  </>;
}

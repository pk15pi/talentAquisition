import axios from 'axios';
const api=axios.create({baseURL:import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'});
api.interceptors.request.use(config=>{const token=localStorage.getItem('access'); if(token) config.headers.Authorization=`Bearer ${token}`; return config;});
export async function login(username:string,password:string){const {data}=await api.post('/auth/token/',{username,password});localStorage.setItem('access',data.access);localStorage.setItem('refresh',data.refresh);return data;}
export function logout(){localStorage.removeItem('access');localStorage.removeItem('refresh');}
export default api;

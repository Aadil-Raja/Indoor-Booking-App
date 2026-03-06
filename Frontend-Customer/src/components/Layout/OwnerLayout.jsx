import Sidebar from './Sidebar';
import './ownerLayout.css';

const OwnerLayout = ({ children }) => {
  return (
    <div className="ib-layout">
      <Sidebar />
      <main className="ib-layout-main">{children}</main>
    </div>
  );
};

export default OwnerLayout;

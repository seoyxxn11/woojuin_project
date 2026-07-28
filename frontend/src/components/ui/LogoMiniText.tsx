type LogoMiniTextProps = {
  text: string;
};

const LogoMiniText = ({ text }: LogoMiniTextProps) => {
  return <span className="text-[13.5px] font-extrabold tracking-[0.05em] text-text-1">{text}</span>;
};

export default LogoMiniText;
